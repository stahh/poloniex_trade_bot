from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render, redirect, render_to_response
from django.core.serializers.json import DjangoJSONEncoder
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.csrf import csrf_protect
from datetime import datetime, timezone, timedelta
import json

from async_bot.helpers.utils import calculate_upper_bottom
from frontend.models import UserExchange, Exchanges
from frontend.forms import UserExchangesForm
from frontend.models import (
    ExchangeCharts, Pair, UserMainCoinPriority, UserPair,
    ToTrade, UserCoinShare, ExchangeCoin, UserOrder, ExchangeTicker, Extremum)


@login_required
def index(request):
    args = {'exchange_form': UserExchangesForm(),
            'ue': UserExchange.objects.all()}
    return render(request, 'trade/home.html', args)


@login_required
def change_status(request):
    try:
        ue = UserExchange.objects.get(pk=request.POST['ue'])
    except ObjectDoesNotExist:
        return HttpResponse('none', status=200)
    ue.is_active = not ue.is_active
    ue.save()
    return HttpResponse('ok', status=200)


@login_required
def exchange(request):
    if request.method == 'POST':
        ue = UserExchange()
        ue.user = request.user
        ue.exchange = Exchanges.objects.get(pk=request.POST.get('exchange'))
        ue.apikey = request.POST.get('apikey')
        ue.apisecret = request.POST.get('apisecret')
        ue.total_btc = float(0)
        ue.save()
    return redirect(index)


@login_required
@csrf_protect
def setup(request, pk):
    args = {}
    try:
        ue = UserExchange.objects.get(pk=pk, user=request.user)
        args['user_exchange'] = ue
        args['user_pairs'] = UserPair.objects.filter(
            user_exchange=args['user_exchange'],
            user=request.user).order_by('-rank')
        primary_coins = ExchangeCoin.objects.filter(
            exchange=ue.exchange)
        active_coins = [x.main_coin for x in
                        UserMainCoinPriority.objects.filter(
                            user_exchange=ue,
                            user_exchange__user=request.user,
                            is_active=True)]
        args['active_coins'] = active_coins
        args['primary_coins'] = primary_coins
        args['to_trade'] = ToTrade.objects.filter(
            user_pair__user_exchange=args['user_exchange'],
            user_pair__user_exchange__user=request.user).order_by(
            '-date_updated')
        args['orders'] = UserOrder.objects.filter(
            ue=args['user_exchange'],
            ue__user=request.user,
            cancel_desc__in=['', 'Worked'],
            ).order_by('-date_updated')
        args['user_coins'] = UserCoinShare.objects.filter(
            user_exchange=args['user_exchange'],
            user_exchange__user=request.user)
        return render(request, 'setup.html', args)
    except ObjectDoesNotExist:
        return redirect('index')


def add_user_pair(request):
    if request.method == 'POST':
        args = {}
        pair_pk = request.POST.get('pair')
        user_exchange_pk = request.POST.get('user-exchange')
        ue = UserExchange.objects.get(pk=user_exchange_pk)
        args['user_exchange'] = ue
        try:
            pair = Pair.objects.get(pk=pair_pk)
            UserPair.objects.get_or_create(
                user=request.user, pair=pair,
                user_exchange_id=user_exchange_pk)
            UserCoinShare.objects.get_or_create(
                user_exchange_id=user_exchange_pk, coin=pair.second_coin)
            args['user_coins'] = UserCoinShare.objects.filter(
                user_exchange=args['user_exchange'])
            args['user_pairs'] = UserPair.objects.filter(
                user_exchange=args['user_exchange']).order_by(
                '-rank')
            return render_to_response('share.html', context=args)
        except ObjectDoesNotExist as e:
            return HttpResponse(e, status=400)


def change_rank(request):
    if request.is_ajax():
        pair_id = request.POST.get('pair_id')
        type_c = request.POST.get('type')
        try:
            user_pair = UserPair.objects.get(pk=pair_id, user=request.user)
            if type_c == 'up':
                user_pair.rank = user_pair.rank + 1
                user_pair.save()
            elif type_c == 'down':
                if user_pair.rank > 1:
                    user_pair.rank = user_pair.rank - 1
                    user_pair.save()
        except ObjectDoesNotExist:
            return HttpResponse('false', status=200)
    return HttpResponse('ok', status=200)


@csrf_protect
def set_share(request):
    args = {}
    user_coin_id = request.POST.get('coin')
    share = request.POST.get('share')
    user_exchange_pk = request.POST.get('user-exchange')
    ue = UserExchange.objects.get(pk=user_exchange_pk)
    args['user_exchange'] = ue
    if float(share) < 0:
        return HttpResponse('Invalid request', status=400)
    # Zero share
    if float(share) == 0:
        try:
            user_coin = UserCoinShare.objects.get(
                pk=user_coin_id, user_exchange_id=user_exchange_pk,
                user_exchange__user=request.user)
            user_coin.share = 0
            user_coin.save()
        except ObjectDoesNotExist:
            return HttpResponse('Not your coin', status=400)
        args['user_coins'] = UserCoinShare.objects.filter(
            user_exchange=args['user_exchange'])
        args['user_pairs'] = UserPair.objects.filter(
            user_exchange=args['user_exchange']).order_by('-rank')
        return render_to_response('share.html', context=args)

    user_coin_share_summ = UserCoinShare.objects.filter(
        user_exchange__user=request.user,
        user_exchange_id=user_exchange_pk).exclude(pk=user_coin_id).aggregate(
            Sum('share'))['share__sum']
    if user_coin_share_summ is None:
        user_coin_share_summ = 0
    if float(user_coin_share_summ) + float(share) > 100:
        return HttpResponse('Sum shares cant be more than 100', status=400)
    try:
        user_coin = UserCoinShare.objects.get(
            pk=user_coin_id, user_exchange__user=request.user)
        user_coin.share = share
        user_coin.save()
    except ObjectDoesNotExist:
        return HttpResponse('Not your coin', status=400)
    args['user_coins'] = UserCoinShare.objects.filter(
        user_exchange=args['user_exchange'])
    args['user_pairs'] = UserPair.objects.filter(
        user_exchange=args['user_exchange']).order_by('-rank')
    return render_to_response('share.html', context=args)


def delete_user_pair(request):
    args = {}
    if request.is_ajax():
        user_pair_id = request.POST.get('pair_id')
        try:
            user_pair = UserPair.objects.get(
                pk=user_pair_id, user=request.user)
            user_pairs_with_this_coin = UserPair.objects.filter(
                pair__second_coin=user_pair.pair.second_coin)
            if len(user_pairs_with_this_coin) == 1:
                to_delete = UserCoinShare.objects.get(
                    coin=user_pair.pair.second_coin,
                    user_exchange=user_pair.user_exchange)
                _ = to_delete.delete()
            user_pair.delete()
            ue = UserExchange.objects.get(pk=user_pair.user_exchange.pk)
            args['user_exchange'] = ue
            args['user_coins'] = UserCoinShare.objects.filter(
                user_exchange=args['user_exchange'])
            args['user_pairs'] = UserPair.objects.filter(
                user_exchange=args['user_exchange']).order_by(
                '-rank')
            return render_to_response('share.html', context=args)
        except ObjectDoesNotExist:
            return HttpResponse('Not your pair', status=400)


def relations(request):
    args = {'exchanges': Exchanges.objects.all()}
    return render(request, 'relations.html', args)


def change_user_exchange_script_activity(request):
    if request.is_ajax():
        user_exch_id = request.POST.get('user_exch')
        try:
            user_exch = UserExchange.objects.get(
                pk=user_exch_id, user=request.user)
            user_exch.is_active_script = not user_exch.is_active_script
            user_exch.save()
            return HttpResponse('true', status=200)
        except ObjectDoesNotExist:
            return HttpResponse('false', status=200)


def change_user_exchange_trade_fake(request):
    if request.is_ajax():
        user_exch_id = request.POST.get('user_exch')
        try:
            user_exch = UserExchange.objects.get(
                pk=user_exch_id, user=request.user)
            user_exch.is_fake_trade = not user_exch.is_fake_trade
            user_exch.save()
            return HttpResponse('true', status=200)
        except ObjectDoesNotExist:
            return HttpResponse('false', status=200)


def change_primary_coin(request):
    if request.is_ajax():
        user_exch_pk = request.POST.get('user_exch')
        ue = UserExchange.objects.get(pk=user_exch_pk)
        coin_pk = request.POST.get('coin')
        coin = ExchangeCoin.objects.get(pk=coin_pk)
        try:
            user_primary_coin = UserMainCoinPriority.objects.get(
                user_exchange=ue, main_coin=coin)
            user_primary_coin.is_active = not user_primary_coin.is_active
            user_primary_coin.save()
        except ObjectDoesNotExist:
            new_user_primary_coin = UserMainCoinPriority()
            new_user_primary_coin.main_coin = coin
            new_user_primary_coin.priority = 1
            new_user_primary_coin.user_exchange = ue
            new_user_primary_coin.is_active = False
            new_user_primary_coin.save()
        return HttpResponse('ok', status=200)


def change_primary_coin_rank(request):
    if request.is_ajax():
        type_r = request.POST.get('type')
        ue_pk = request.POST.get('user_exch')
        coin_pk = request.POST.get('coin')
        ue = UserExchange.objects.get(pk=ue_pk)
        coin = ExchangeCoin.objects.get(pk=coin_pk)
        try:
            user_primary_coin = UserMainCoinPriority.objects.get(
                user_exchange=ue, main_coin=coin)
            if type_r == 'up':
                user_primary_coin.priority += 1
            elif type_r == 'down':
                if user_primary_coin.priority > 1:
                    user_primary_coin.priority -= 1
            user_primary_coin.save()
        except ObjectDoesNotExist:
            new_user_primary_coin = UserMainCoinPriority()
            new_user_primary_coin.main_coin = coin
            if type_r == 'up':
                new_user_primary_coin.priority = 2
            else:
                new_user_primary_coin.priority = 1
            new_user_primary_coin.user_exchange = ue
            new_user_primary_coin.is_active = True
            new_user_primary_coin.save()
        return HttpResponse('ok', status=200)


def set_pair_add(request):
    if request.method == 'POST':
        pair_pk = request.POST.get('pair-pk')
        user_exchange_pk = request.POST.get('user-exchange-pk')
        rate_of_change = request.POST.get('rate_of_change')
        if rate_of_change == '':
            rate_of_change = 0
        try:
            UserPair.objects.filter(
                pk=pair_pk, user_exchange_id=user_exchange_pk).update(
                rate_of_change=rate_of_change)
        except ObjectDoesNotExist:
            pass
        return redirect('/trade/setup/' + str(user_exchange_pk) + '/')
    else:
        return redirect('/')


def get_new_to_trade(request):
    if request.is_ajax():
        ue_pk = request.POST.get('user_exch')
        already = request.POST.get('already')
        to_trade = ToTrade.objects.filter(user_pair__user_exchange_id=ue_pk)
        if len(to_trade) != int(already):
            return render(request, 'to_trade.html', {'to_trade': to_trade})
        else:
            return HttpResponse('ok', status=200)


def exchange_depth_to_trade(request):
    if request.method == 'POST':
        depth = request.POST.get('depth')
        exchange_pk = request.POST.get('user-exchange-pk')
        if depth == '':
            depth = 0
        try:
            ue = UserExchange.objects.get(user=request.user, pk=exchange_pk)
            ue.coefficient_of_depth = depth
            ue.save()
        except ObjectDoesNotExist:
            pass
        return redirect('/trade/setup/' + str(exchange_pk) + '/')
    else:
        return HttpResponse('Please use POST request', status=200)


def get_ticker(request):
    if request.is_ajax():
        user_pair_id = request.POST.get('user_pair_id')
        pair_id = request.POST.get('pair_id')
        interval = int(request.POST.get('intervale'))
        zoom = request.POST.get('zoom')
        exchange = request.POST.get('exchange')
        charts = {}
        tickers = []
        extremums = []
        intervals = []
        order_list = []

        if user_pair_id:
            user_pair = UserPair.objects.values('pair_id').get(pk=user_pair_id)
            pair_id = user_pair.get('pair_id')

        if zoom == 'all':
            zoom = 60

        if zoom == 60 or interval == 120:
            tickers = list(ExchangeCharts.objects.filter(
                pair_id=pair_id, exchange_id=exchange))
            if tickers:
                for ticker in tickers:
                    tickers.append(
                        {'date': ticker.date_time,
                         'open': ticker.open,
                         'close': ticker.close,
                         'low': ticker.low,
                         'high': ticker.high})
        else:
            q = ExchangeTicker.objects.values(
                'date_time', 'last').filter(
                pair_id=pair_id,
                date_time__gte=datetime.now(timezone.utc) - timedelta(
                    hours=int(zoom)), exchange_id=exchange)
            ticker = list(q)
            if len(ticker) > 0:
                ext = Extremum.objects.values(
                    'date', 'price', 'ext_type').filter(
                    pair_id=pair_id, date__gte=ticker[0]['date_time'])
                for item in ext:
                    extremums.append(
                        [item['date'], item['price'], item['ext_type']])
                s_date = datetime.now(timezone.utc)
                for t in ticker:
                    if t['date_time'].minute % interval == 0:
                        s_date = t['date_time']
                        break
                while s_date <= datetime.now(timezone.utc) + timedelta(
                        minutes=interval):
                    intervals.append(s_date)
                    s_date = s_date + timedelta(minutes=interval)

                if len(intervals) > 0:
                    s_chain = [x for x in ticker if
                               s_date + timedelta(minutes=interval) > x[
                                   'date_time'] >= s_date]

                    while len(intervals) > 0:
                        try:
                            tickers.append(
                                {'date': s_date,
                                 'open': s_chain[0]['last'],
                                 'close': s_chain[-1]['last'],
                                 'low': min(
                                     [x['last'] for x in s_chain]),
                                 'high': max(
                                     [x['last'] for x in s_chain])})
                        except IndexError:
                            pass
                        s_date = intervals.pop(0)
                        s_chain = [x for x in ticker if
                                   s_date + timedelta(minutes=interval)
                                   > x['date_time'] >= s_date]

        _, _, upper_line, bottom_line = calculate_upper_bottom(
            Pair.objects.get(pk=pair_id))

        orders = UserOrder.objects.filter(
            cancel_desc='Worked', pair_id=pair_id,
            date_created__gte=datetime.now(timezone.utc) - timedelta(
                    hours=int(zoom)))
        if orders:
            for order in orders:
                order_list.append(
                    {'order_type': order.order_type,
                     'order_number': order.order_number,
                     'amount': order.amount,
                     'fact_amount': order.second_coin_after_total,
                     'price': order.price,
                     'btc_spent': order.fact_total,
                     'date': order.date_created})
        charts['ticker'] = tickers[-60:] if len(tickers) > 60 else tickers
        charts['extremums'] = extremums
        charts['orders'] = order_list
        charts['upper_line'] = upper_line
        charts['bottom_line'] = bottom_line
        json_data = json.dumps(charts, cls=DjangoJSONEncoder)
        return HttpResponse(json_data, status=200)
