from datetime import datetime, timezone, timedelta
import time
import jsonpickle
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from async_bot.helpers.models import (
    UserBalance, UserPair, ToTrade, UserMainCoinPriority, UserCoinShare,
    UserOrder, create, get_first_by_filter, update_model, Pair)
from frontend.settings import (SQLALCHEMY_ENGINE, DEPTH_COEFFICIENT,
                               ORDER_TTL, FEE, ALLOWED_BUY, STRICT_TRADE)
from async_bot.helpers.telegramm_bot import send_telegram
from async_bot.helpers.utils import calculate_upper_bottom
from async_bot.helpers.utils import get_logger

engine = create_engine(SQLALCHEMY_ENGINE)
Session = sessionmaker(bind=engine)
session = Session()
log = get_logger('calculator')


class BidsAsksTypeException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


async def delta(x):
    try:
        v = float(x) * 100000
        if v < 1:
            return 0.00000001
        elif 10 > v >= 1:
            return 0.00001
        elif 100 > v >= 10:
            return 0.0001
        elif 1000 > v >= 100:
            return 0.001
        elif 10000 > v >= 1000:
            return 0.01
        elif 100000 > v >= 10000:
            return 0.1
        elif 1000000 > v >= 100000:
            return 1
        else:
            return 0.00000001
    except Exception as e:
        log.exception(e)


async def calculate_full_order_book(book):
    try:
        for item in book:
            item.append(str(float(item[0]) * float(item[1])))
        return book
    except Exception as e:
        log.error(f'calculate_full_order_book error: {e}')


async def get_last_max_price(user_pair, need_log=False):
    try:
        last_orders = session.query(UserOrder).filter(
            UserOrder.ue_id == user_pair.user_exchange.id,
            UserOrder.pair_id == user_pair.pair.id,
            UserOrder.cancel_desc == 'Worked').order_by(
            -UserOrder.date_created).all()[:20]

        prices = []
        last_ord_num = None
        for trade in last_orders:
            if trade.order_type == 'sell' and last_ord_num:
                break
            if trade.order_type == 'buy':
                last_ord_num = trade.order_number
                prices.append(trade.price)
        if not prices:
            return
        max_price = max(prices)

        if need_log and last_ord_num:
            log.info(f'Последний ордер на покупку № '
                     f'{last_ord_num}, по цене {max_price: .8f}')
        return max_price
    except Exception as e:
        log.error(f'get_last_max_price Error: {e}')


async def calculate_price(amount=0, o_type=None, bids=None, asks=None):
    try:
        if amount == 0:
            return 0
        if o_type == 'buy' and bids is None:
            raise BidsAsksTypeException('No volume to buy')
        if o_type == 'sell' and asks is None:
            raise BidsAsksTypeException('No volume to sell')

        depth = float(DEPTH_COEFFICIENT) * float(amount)

        if o_type == 'buy':
            bids = await calculate_full_order_book(bids)
            sum_t = float(0)
            for i in range(len(bids)):
                sum_t += float(bids[i][1])
                if sum_t >= depth:
                    return float(bids[i][0]) + 0.00000001
        elif o_type == 'sell':
            asks = await calculate_full_order_book(asks)
            sum_t = float(0)
            for i in range(len(asks)):
                sum_t += float(asks[i][1])
                if sum_t >= depth:
                    return float(asks[i][0]) - 0.00000001
    except Exception as e:
        log.error(f'calculate_price Error: {e}')


async def is_need_sell(user_pair, last_ask, asks):
    try:
        max_price = await get_last_max_price(user_pair)
        sell_price = float(last_ask) + await delta(last_ask) * 10
        if max_price and sell_price >= max_price:
            if STRICT_TRADE:
                user_balance_second_coin = await get_first_by_filter(
                    session=session, model=UserBalance,
                    ue_id=user_pair.user_exchange.id,
                    coin=user_pair.pair.second_coin.symbol.lower())
                available_sell_coin = user_balance_second_coin.free

                if available_sell_coin < 0.001:
                    return False
                price = await calculate_price(
                    amount=available_sell_coin, o_type='sell', asks=asks)
                total_in_btc = available_sell_coin * float(price)
                total_without_fee = total_in_btc - total_in_btc * FEE * 2
                need_sell = await check_need_sell(
                        user_pair, total_without_fee,
                        available_sell_coin, price)
                if not need_sell:
                    return False
            log.warning(f'!!! {user_pair.pair} Sell without extremum! '
                        f'Last buy order price {max_price: .8f}, '
                        f'current ask - {float(last_ask): .8f}')
            return True
        return False
    except Exception as e:
        log.exception(f'Method is_need_sell Error: {e}')
        send_telegram(
            title='ERROR',
            text=f'Method is_need_sell Error: {e}')
        return False


async def check_last_sell_and_priority(user_pair):
    try:
        last_sell_order = session.query(UserOrder.date_updated).filter(
            UserOrder.ue_id == user_pair.user_exchange.id,
            UserOrder.pair_id == user_pair.pair.id,
            UserOrder.order_type == 'sell',
            UserOrder.cancel_desc == 'Worked').order_by(
            UserOrder.date_updated).first()

        try:
            if (last_sell_order and last_sell_order.date_updated >
                    datetime.now(timezone.utc) - timedelta(minutes=ORDER_TTL)):
                log.info(f'It\'s not time to buy yet. Last sell order '
                         f'was closed on {last_sell_order.date_updated}')
                return True
        except:
            if (last_sell_order and last_sell_order.date_updated >
                    datetime.now() - timedelta(minutes=ORDER_TTL)):
                log.info(f'It\'s not time to buy yet. Last sell order '
                         f'was closed on {last_sell_order.date_updated}')
                return True
        user_main_coin = await get_first_by_filter(
            session=session, model=UserMainCoinPriority,
            user_exchange_id=user_pair.user_exchange.id,
            main_coin_id=user_pair.pair.main_coin.id)
        if not user_main_coin or not user_main_coin.is_active:
            log.info(f'Coin [{user_main_coin}] has no priority or not active')
            return True
        return False
    except Exception as e:
        log.error(f'Method check_last_sell_and_priority Error: {e}')


async def enough_percent(user_pair, user_balance_second_coin):
    try:
        user_balance_second_coin_in_btc = user_balance_second_coin.btc_value
        user_second_coin_percent = user_balance_second_coin_in_btc / (
                user_pair.user_exchange.total_btc / 100)
        user_coin_share = await get_first_by_filter(
            session=session, model=UserCoinShare,
            user_exchange_id=user_pair.user_exchange.id,
            coin_id=user_pair.pair.second_coin.id)
        user_need_second_coin_in_percent = user_coin_share.share
        missing_in_btc = user_need_second_coin_in_percent - \
            user_second_coin_percent
        if missing_in_btc < 0.5:
            log.warning(f'Lack of percentage '
                        f'{abs(missing_in_btc): .2f}. Balance '
                        f'{user_balance_second_coin_in_btc} '
                        f'{user_pair.second_coin}')
            return False
        # calculate priorities
        sum_priority_second_coin = session.query(
            func.sum(UserPair.rank).label('sum_rank')).filter(
            UserPair.user_exchange_id == user_pair.user_exchange_id,
            UserPair.pair_id == user_pair.pair_id).first().sum_rank
        user_need_to_buy_on_prior = float(missing_in_btc) * (
                float(user_pair.rank) / float(sum_priority_second_coin))
        user_need_to_buy_in_btc = \
            (user_pair.user_exchange.total_btc / 100) * \
            user_need_to_buy_on_prior
        return user_need_to_buy_in_btc
    except Exception as e:
        log.error(f'Method enough_percent Error:{e}')


async def check_need_sell(
        user_pair, total_without_fee, amount, price, logs=False):
    try:
        max_price = await get_last_max_price(user_pair, logs)

        last_buy_in_btc = amount * max_price

        if last_buy_in_btc < total_without_fee:
            return True
        if logs:
            log.warning(f'I won\'t sell it, I bought it at '
                        f'{max_price: .8f} on {last_buy_in_btc: .8f} '
                        f'btc, sell out at {price: .8f} '
                        f'on {total_without_fee: .8f} btc')
        return False
    except Exception as e:
        log.error(f'Method check_need_sell Error: {e}')
        send_telegram(
            title='ERROR',
            text=f'Method check_need_sell Error: {e}')


async def is_forbidden_buy(user_pair, polo):
    try:

        charts = polo.returnChartData(
            currencyPair=user_pair.name, period=300,
            start=int(time.time() - timedelta(minutes=30).seconds),
            end=int(time.time()))
        diffs = []
        for l in charts[1:6]:
            diffs.append(l.get('open') - l.get('close'))

        if all(x > 0 for x in diffs):
            return True  # forbidden buy
        return False
    except Exception as e:
        log.error(f'Method is_forbidden_buy Error: {e}')


async def calculate_order_for_user(user_pair, params, order_type, polo):
    try:
        point = await get_first_by_filter(
            session=session, model=Pair, id=user_pair.pair_id)
        upper_y3, bottom_y3, _, _ = calculate_upper_bottom(point)

        user_balance_second_coin = await get_first_by_filter(
            session=session, model=UserBalance,
            ue_id=user_pair.user_exchange.id,
            coin=user_pair.pair.second_coin.symbol.lower())

        user_balance_main_coin = await get_first_by_filter(
            session=session, model=UserBalance,
            ue_id=user_pair.user_exchange.id,
            coin=user_pair.pair.main_coin.symbol.lower())

        pr = f'{user_pair.pair.second_coin.symbol.lower()}_' \
             f'{user_pair.pair.main_coin.symbol.lower()}'

        if order_type == 'buy':
            log.info(f"Calculating buy "
                     f"{user_pair.second_coin} for BTC")
            if not ALLOWED_BUY:
                log.warning('Buying is prohibited')
                return

            if await is_forbidden_buy(user_pair, polo):
                log.warning(f'{pr}: The previous 5 bars were bull\'s. '
                            f'Don\'t buy')
                send_telegram(
                    title='Warning',
                    text=f'{pr}: The previous 5 bars were bull\'s. Don\'t buy')
                return

            if await check_last_sell_and_priority(user_pair):
                return

            user_need_to_buy_in_btc = await enough_percent(
                user_pair, user_balance_second_coin)
            if not user_need_to_buy_in_btc:
                return

            log.info(f'Need take in BTC: {user_need_to_buy_in_btc}')

            if user_pair.main_coin == 'BTC':
                user_need_to_buy_in_first_coin = user_need_to_buy_in_btc
            else:
                ticker_list = jsonpickle.decode(params['ticker'])
                try:
                    ticker = ticker_list.get_ticker_by_name(
                        'BTC_' + user_pair.pair.main_coin.symbol.upper())
                    user_need_to_buy_in_first_coin = float(
                        user_need_to_buy_in_btc) / float(ticker.last)
                except AttributeError as e:
                    log.error(
                        f'TICKER LAST NOT FOUND BTC_'
                        f'{user_pair.main_coin}: {e}')
                    ticker = ticker_list.get_ticker_by_name(
                        user_pair.main_coin + '_BTC')
                    user_need_to_buy_in_first_coin = float(
                        user_need_to_buy_in_btc) * float(ticker.last)
                except Exception:
                    log.error(
                        f'[+++] MISSING COIN {user_pair.pair.main_coin}')
                    send_telegram(
                        title='ERROR',
                        text=f'[+++] MISSING COIN {user_pair.pair.main_coin}')
                    return

            if not user_balance_main_coin:
                log.warning('Coin not found!')
                return
            if user_balance_main_coin.free < 0.0001:
                log.warning(f'Coin '
                            f'{user_pair.main_coin}, '
                            f'available {user_balance_main_coin.free}')
                return
            if user_balance_main_coin.free < user_need_to_buy_in_first_coin:
                user_need_to_buy_in_first_coin = user_balance_main_coin.free

            bids = params['bids']
            price = await calculate_price(user_need_to_buy_in_first_coin,
                                          o_type='buy', bids=bids)
            if (STRICT_TRADE and price > bottom_y3
                    and price > upper_y3 - upper_y3 * FEE * 10):
                log.warning(f'{pr} Current price {price: .8f} '
                            f'too close to the top limit е {upper_y3: .8f}, '
                            f'diff: {upper_y3 * FEE * 10: .8f}, '
                            f'minimum: {upper_y3 - upper_y3 * FEE * 10: .8f}. '
                            f'The lowest price: {bottom_y3: .8f} .'
                            f'Don\'t buy')
                return
            total_in_btc = user_need_to_buy_in_first_coin / price
            if total_in_btc < 0.0001:
                log.info(f'Need to buy < 0.0001: {total_in_btc} too less')
                return
            log.info(f'I want to spend {user_need_to_buy_in_first_coin: .8f} '
                     f'{user_pair.main_coin} to buy '
                     f'{total_in_btc: .8f} '
                     f'{user_pair.second_coin}\n'
                     f'Calculate by {price}')
            to_trade = await get_first_by_filter(
                session=session, model=ToTrade,
                user_pair=user_pair, type='buy')
            try:
                try:
                    data = {
                        'price': price,
                        'amount': total_in_btc,
                        'total': user_need_to_buy_in_first_coin,
                        'total_f': user_need_to_buy_in_first_coin - (
                                user_need_to_buy_in_first_coin * FEE),
                        'cause': 'Change rate',
                        'date_updated': datetime.now(timezone.utc)
                    }
                    await update_model(session=session,
                                       model=ToTrade,
                                       pk=to_trade.id, data=data)
                    log.info(f'Updated to trade order: {to_trade}, {data}')
                except Exception:
                    data = {
                        'user_pair_id': user_pair.id,
                        'type': 'buy',
                        'price': price,
                        'amount': total_in_btc,
                        'total': user_need_to_buy_in_first_coin,
                        'total_f': user_need_to_buy_in_first_coin - (
                                user_need_to_buy_in_first_coin * FEE),
                        'fee': FEE,
                        'cause': 'New',
                        'date_created': datetime.now(timezone.utc),
                        'date_updated': datetime.now(timezone.utc)
                    }
                    await create(session=session, model=ToTrade, **data)
                    log.info(f'Open to trade order: {data}')
            except Exception as e:
                log.error(f'Error creating BUY ToTrade order: {e}')
                send_telegram(
                    title='ERROR',
                    text=f'Error creating BUY ToTrade order: {e}')
        elif order_type == 'sell':
            available_sell_coin = user_balance_second_coin.free
            log.info(f'Calculating Sell '
                     f'{user_pair.second_coin}'
                     f' for {user_pair.main_coin}')

            if available_sell_coin < 0.001:
                return
            asks = params['asks']
            price = await calculate_price(
                amount=available_sell_coin, o_type='sell', asks=asks)
            total_in_btc = available_sell_coin * float(price)
            total_without_fee = total_in_btc - total_in_btc * FEE
            log.info(f'First coin: {available_sell_coin: .8f} * '
                     f'found price: {price: .8f} = total '
                     f'without fee: {total_in_btc: .8f}, '
                     f'Fee: {total_in_btc * FEE: .8f}')
            if STRICT_TRADE and not await check_need_sell(
                    user_pair, total_without_fee,
                    available_sell_coin, price, True):
                return

            log.info(f'I want to spend  {available_sell_coin: .8f} '
                     f'{user_pair.econd_coin} to buy '
                     f'{total_in_btc} {user_pair.main_coin}')
            to_trade = await get_first_by_filter(
                session=session, model=ToTrade, user_pair=user_pair,
                type='sell', amount=available_sell_coin)
            try:
                try:
                    data = {
                        'price': price,
                        'amount': available_sell_coin,
                        'total': total_in_btc,
                        'total_f': total_without_fee,
                        'date_updated': datetime.now(timezone.utc),
                        'cause': 'Change rate'
                    }
                    await update_model(session=session,
                                       model=ToTrade,
                                       pk=to_trade.id, data=data)
                    log.info(f'Updated to trade order: {to_trade}, {data}')
                except Exception:
                    data = {
                        'user_pair_id': user_pair.id,
                        'type': 'sell',
                        'price': price,
                        'amount': available_sell_coin,
                        'total': total_in_btc,
                        'total_f': total_without_fee,
                        'fee': FEE,
                        'cause': 'New',
                        'date_created': datetime.now(timezone.utc),
                        'date_updated': datetime.now(timezone.utc)
                    }
                    await create(session=session, model=ToTrade, **data)
                    log.info(f'Open to trade order: {data}')
            except Exception as e:
                log.error(f'Error creating SELL ToTrade order: {e}')
                send_telegram(
                    title='ERROR',
                    text=f'Error creating SELL ToTrade order: {repr(e)}')
        else:
            log.error('Incorrect Order Type')
    except Exception as e:
        log.error(f'Method calculate_order_for_user Error: {e}')
