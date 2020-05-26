import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from frontend.settings import (SQLALCHEMY_ENGINE, ORDER_TTL, FEE,
                               POLONIEX_API_KEY, POLONIEX_API_SECRET)
from async_bot.helpers.telegramm_bot import send_telegram
from async_bot.helpers.models import (UserExchange, get_by_filter, create,
                                      get_first_by_filter, update_model)
from async_bot.helpers.models import UserBalance
from async_bot.helpers.models import ToTrade, UserOrder
from async_bot.helpers.utils import get_usd_value, get_logger
from poloniex import Poloniex

engine = create_engine(SQLALCHEMY_ENGINE)
Session = sessionmaker(bind=engine)
session = Session()


class Checker:

    def __init__(self, ex_ev):
        self.ex_ev = ex_ev
        self.log = None
        self.loop = asyncio.new_event_loop()
        self.polo = Poloniex(POLONIEX_API_KEY, POLONIEX_API_SECRET)

    async def eternity(self, timeout):
        while not self.ex_ev.is_set():
            await asyncio.sleep(timeout)

    async def get_balance(self, balances, user_exchange):

        total_btc = float(0)
        for coin, balance in balances.items():
            total_balance = float(balance['available']) + \
                            float(balance['onOrders'])

            total_btc += float(balance['btcValue'])
            try:
                coin_balance = await get_first_by_filter(
                    session=session, model=UserBalance, ue=user_exchange,
                    coin=coin.lower())
            except Exception as e:
                self.log.error(f'Error getting coin balance: {e}')
                send_telegram(
                    title='ERROR', text=f'Error getting coin balance: {e}')
                coin_balance = None
            if coin_balance:
                data = {
                    'total': total_balance,
                    'btc_value': balance['btcValue'],
                    'conversions': '',
                    'used': balance['onOrders'],
                    'free': balance['available'],
                    'last_update': datetime.now(timezone.utc)
                }
                await update_model(session=session,
                                   model=UserBalance,
                                   pk=coin_balance.id, data=data)
            else:
                data = {
                    'ue_id': user_exchange.id,
                    'coin': coin,
                    'total': total_balance,
                    'btc_value': balance['btcValue'],
                    'conversions': '',
                    'used': balance['onOrders'],
                    'free': balance['available'],
                    'last_update': datetime.now(timezone.utc)
                }
                await create(session=session, model=UserBalance, **data)
        # =================================================
        data = {
            'total_btc': total_btc,
            'total_usd': get_usd_value('btc', total_btc),
            'error': '',
        }
        await update_model(session=session,
                           model=UserExchange,
                           pk=user_exchange.id, data=data)

    async def pull_exchanges_balances(self, ue_pk=None):
        while not self.ex_ev.is_set():
            # print("=========CHECKER PULL EXCHANGE BALANCE========")
            try:
                if ue_pk is None:
                    user_exchanges = await get_by_filter(
                        session=session, model=UserExchange)
                else:
                    user_exchanges = await get_by_filter(
                        session=session, model=UserExchange, id=ue_pk)
            except Exception as e:
                self.log.error(f'Get Exchange Error: {e}')
                return
            if not user_exchanges:
                self.log.error('No Active Exchanges!')
            for user_exchange in user_exchanges:
                try:
                    balances = self.polo.returnCompleteBalances()
                    try:
                        await self.get_balance(balances, user_exchange)
                    except Exception as e:
                        self.log.error(f'Get Balance Error: {e}')
                        send_telegram(
                            title='ERROR', text=f'Get Balance Error: {e}')

                    data = {
                        'error': '',
                        'is_correct': True,
                        'is_active': True
                    }
                    await update_model(session=session,
                                       model=UserExchange,
                                       pk=user_exchange.id, data=data)
                except Exception as e:
                    self.log.error(f'Get Balance From Poloniex Error: {e}')
                    send_telegram(
                        title='ERROR', text='Incorrect apikey or secret')
                    data = {
                        'error': 'Incorrect apikey or secret',
                        'is_correct': False,
                        'is_active': False
                    }
                    await update_model(session=session,
                                       model=UserExchange,
                                       pk=user_exchange.id, data=data)
            if self.ex_ev.is_set():
                break
            try:
                await asyncio.wait_for(self.eternity(10), timeout=60.0)
            except asyncio.TimeoutError:
                ...

            if ue_pk:
                break
        if self.ex_ev.is_set():
            self.log.info('=========EXIT EVENT PULL EXCHANGE BALANCE========')

    async def check_open(self, uo, orders_to_close):
        if uo in orders_to_close:
            self.log.info(f'Time to close for order # '
                          f'{uo.order_number} {uo.pair}')
            canceled = {}
            i = 3
            if uo.is_fake:
                canceled['success'] = 1
            else:
                while not self.ex_ev.is_set():
                    try:
                        self.log.info(f'Trying to cancel order '
                                      f'{uo.order_number} {uo.pair}')
                        canceled = self.polo.cancelOrder(
                            str(uo.order_number))
                    except Exception as e:
                        self.log.error(f'Cancel order error: {e}')
                        await asyncio.sleep(.5)
                        self.polo = Poloniex(POLONIEX_API_KEY,
                                             POLONIEX_API_SECRET)
                        if 'success' in e:
                            canceled['success'] = 1
                    if canceled or i == 0:
                        break
                    i -= 1
            if canceled['success'] == 1:
                data = {
                    'date_cancel': datetime.now(timezone.utc),
                    'date_updated': datetime.now(timezone.utc),
                    'cancel_desc': 'TTL'
                }
                try:
                    await update_model(session=session,
                                       model=UserOrder,
                                       pk=uo.id, data=data)
                    self.log.info(
                        f'Order # {uo.order_number}({uo.pair}) '
                        f'was canceled')
                    send_telegram(
                        title='Order was canceled',
                        text=f'Order # {uo.order_number}({uo.pair}) '
                             f'was canceled')
                except Exception as e:
                    self.log.error(
                        f'Order # {uo.order_number} update error {e}')
                    send_telegram(
                        title='ERROR',
                        text=f'Order # {uo.order_number} update error {e}')
        else:
            balance_main_coin = await get_first_by_filter(
                session=session, model=UserBalance, ue=uo.ue,
                coin=uo.pair.main_coin.symbol.lower())
            if balance_main_coin:
                try:
                    data = {
                        'interim_main_coin': balance_main_coin.total,
                        'date_updated': datetime.now(timezone.utc),
                    }
                    await update_model(session=session,
                                       model=UserOrder,
                                       pk=uo.id, data=data)
                except Exception as e:
                    self.log.error(
                        f'Order # {uo.order_number} update error {e}')
                    send_telegram(
                        title='ERROR',
                        text=f'Order # {uo.order_number} update error {e}')

    async def check_close(self, uo):

        current_balance_main_coin = await get_first_by_filter(
            session=session, model=UserBalance, ue=uo.ue,
            coin=uo.pair.main_coin.symbol.lower()
        )
        fact_total = 0
        data = {}

        if current_balance_main_coin:
            data['main_coin_after_total'] = current_balance_main_coin.total
            data['main_coin_after_free'] = current_balance_main_coin.free
            data['main_coin_after_used'] = current_balance_main_coin.used
        else:
            data['main_coin_after_total'] = '-1'
            data['main_coin_after_free'] = '-1'
            data['main_coin_after_used'] = '-1'

        current_balance_second_coin = await get_first_by_filter(
            session=session, model=UserBalance, ue=uo.ue,
            coin=uo.pair.second_coin.symbol.lower()
        )
        if current_balance_second_coin:
            data['second_coin_after_total'] = current_balance_second_coin.total
            data['second_coin_after_used'] = current_balance_second_coin.free
            data['second_coin_after_free'] = current_balance_second_coin.used
        else:
            data['second_coin_after_total'] = '-1'
            data['second_coin_after_used'] = '-1'
            data['second_coin_after_free'] = '-1'

        if uo.order_type == 'buy':
            fact_total = float(uo.interim_main_coin) - float(
                current_balance_main_coin.total)
        if uo.order_type == 'sell':
            fact_total = float(current_balance_main_coin.total) - float(
                uo.interim_main_coin)

        data['fact_total'] = fact_total
        if fact_total != 0:
            fact_fee = 100.0 * float(uo.total) / float(fact_total) - 100.0
            data['fact_fee'] = fact_fee
            if fact_fee > 0.2:
                data['is_ok'] = False
        try:
            data['to_close'] = False
            data['cancel_desc'] = 'Worked'
            data['date_updated'] = datetime.now(timezone.utc)
            data['date_cancel'] = datetime.now(timezone.utc)
            await update_model(session=session,
                               model=UserOrder,
                               pk=uo.id, data=data)

            self.log.warning(f'[!!!!!] Order # {uo.order_number}, '
                             f'Pair {uo.pair} saved [!!!!!]')
            send_telegram(
                title='!!! Order saved',
                text=f'Order # {uo.order_number}, '
                     f'Pair {uo.pair} saved')
        except Exception as e:
            self.log.error(f'Save Order Error: {e}')
            send_telegram(
                title='ERROR',
                text=f'Save Order Error: {e}')

    async def group_check_orders(self, uo, orders_to_close):
        try:
            order_status = self.polo.returnOrderStatus(
                uo.order_number)
            if order_status.get('success') == 1:
                await self.check_open(uo, orders_to_close)
            if order_status.get('success') == 0:
                await self.check_close(uo)
        except Exception as e:
            self.log.error(f'Error getting orders for {uo.order_number}: {e}')
            send_telegram(
                title='ERROR',
                text=f'Error getting orders for {uo.order_number}: {e}')

    async def check_orders(self):
        while not self.ex_ev.is_set():
            # print('===========CHECKER CHECK ORDERS================')
            user_orders = None
            try:
                user_orders = await get_by_filter(
                    session=session, model=UserOrder, cancel_desc='')
            except Exception as e:
                self.log.error(f'Error getting user orders to close: {e}')

            if user_orders:
                try:
                    orders_to_close = session.query(UserOrder).filter(
                        UserOrder.date_created <= datetime.now(timezone.utc) -
                        timedelta(minutes=ORDER_TTL),
                        UserOrder.cancel_desc == '',
                        UserOrder.to_close.is_(False)).all()
                    [asyncio.ensure_future(
                        self.group_check_orders(uo, orders_to_close),
                        loop=self.loop)
                        for uo in user_orders]

                except Exception as e:
                    self.log.error(f'Check orders error: {e}')
                    send_telegram(
                        title='ERROR',
                        text=f'Check orders error: {e}')

            await asyncio.sleep(1)

        if self.ex_ev.is_set():
            self.log.info('==========CHECKER EXIT EVENT check_orders=======')

    async def open_real_order(self, to_trade):
        pair = f'{to_trade.user_pair.main_coin}_' \
               f'{to_trade.user_pair.second_coin}'
        order_id = None
        try:
            if to_trade.type == 'buy':
                order = self.polo.buy(
                    currencyPair=pair, rate=to_trade.price,
                    amount=to_trade.amount, postOnly=1)
                self.log.warning(f'Answer (buy): {order}')
                order_id = order.get('orderNumber')
                send_telegram(
                    title=f'Order open: {pair}, '
                          f'price: {to_trade.price: .8f}, '
                          f'amount: {to_trade.amount}',
                    text=f'Answer (buy): {order}')
            elif to_trade.type == 'sell':
                order = self.polo.sell(
                    currencyPair=pair, rate=to_trade.price,
                    amount=to_trade.amount, postOnly=1)
                self.log.warning(f'Answer (sell): {order}')
                order_id = order.get('orderNumber')
                send_telegram(
                    title=f'Order open: {pair}, '
                          f'price: {to_trade.price: .8f}, '
                          f'amount: {to_trade.amount}',
                    text=f'Answer (sell): {order}')
        except Exception as e:
            self.log.error(f'Open order {pair}, {to_trade.amount}, '
                           f'{to_trade.price}. Error: {e}')
            send_telegram(
                title='ERROR',
                text=f'Open order for: {pair}, amount: {to_trade.amount}, '
                     f'price: {to_trade.price: .8f}. Error: {e}')
            await asyncio.sleep(1)

        return order_id

    async def check_to_trade(self):

        while not self.ex_ev.is_set():
            # print('================CHECK TO TRADE===================')
            try:
                to_trade = session.query(ToTrade).filter(
                    ToTrade.date_updated >= datetime.now(timezone.utc) -
                    timedelta(minutes=5)).order_by(
                    ToTrade.date_updated).first()
                if not to_trade:
                    await asyncio.sleep(5)
                    continue
                self.log.info(f'Found order to trade: {to_trade}')
                already_in_orders = await get_by_filter(
                    session=session, model=UserOrder,
                    pair_id=to_trade.user_pair.pair.id,
                    date_cancel=None)

                self.log.info(f'Already in orders: {already_in_orders}')
                if len(already_in_orders) > 0:
                    to_delete = session.query(ToTrade).filter(
                        ToTrade.id == to_trade.id)
                    _ = to_delete.delete()
                    session.commit()
                else:
                    self.log.info('Trying to open order...')
                    order_id = await self.open_real_order(to_trade)
                    if not order_id:
                        await asyncio.sleep(5)
                        continue

                    await self.pull_exchanges_balances(
                        to_trade.user_pair.user_exchange.id)
                    self.log.info('Balance Checked')
                    main_coin_balance = await get_first_by_filter(
                        session=session, model=UserBalance,
                        ue=to_trade.user_pair.user_exchange,
                        coin=to_trade.user_pair.pair.main_coin.symbol
                    )
                    second_coin_balance = await get_first_by_filter(
                        session=session, model=UserBalance,
                        ue=to_trade.user_pair.user_exchange,
                        coin=to_trade.user_pair.pair.second_coin.symbol
                    )
                    self.log.info(f'Main coin: {main_coin_balance}, '
                                  f'Second coin: {second_coin_balance}')

                    data = {
                        'ue_id': to_trade.user_pair.user_exchange.id,
                        'pair_id': to_trade.user_pair.pair.id,
                        'order_type': to_trade.type,
                        'order_number': order_id,
                        'interim_main_coin': main_coin_balance.total,
                        'main_coin_before_total': main_coin_balance.total,
                        'main_coin_before_free': main_coin_balance.free,
                        'main_coin_before_used': main_coin_balance.used,
                        'second_coin_before_total': second_coin_balance.total,
                        'second_coin_before_free': second_coin_balance.free,
                        'second_coin_before_used': second_coin_balance.used,
                        'price': to_trade.price,
                        'amount': to_trade.amount,
                        'total': to_trade.price * to_trade.amount,
                        'date_created': datetime.now(timezone.utc),
                        'date_updated': datetime.now(timezone.utc),
                        'fee': FEE,
                    }
                    self.log.info('Create order')
                    try:
                        await create(session=session, model=UserOrder, **data)
                        self.log.warning(f"Order {order_id} added. "
                                         f"Type {to_trade.type}, "
                                         f"Pair {to_trade.user_pair.pair}, "
                                         f"Price {to_trade.price: .8f}")
                        to_delete = session.query(ToTrade).filter(
                            ToTrade.id == to_trade.id)
                        _ = to_delete.delete()
                        session.commit()
                    except Exception as e:
                        self.log.exception(f'Create Order Error: {e}')
                        send_telegram(
                            title='ERROR',
                            text=f'Error write order to DB: {e}')
            except Exception as e:
                self.log.error(f'check_to_trade error: {e}')
            await asyncio.sleep(5)

        if self.ex_ev.is_set():
            self.log.info('============CHECK TO TRADE EXIT EVENT===========')

    def run(self):
        self.log = get_logger('checker')
        self.log.info('Start Checker')
        asyncio.set_event_loop(self.loop)
        tasks = [
            self.pull_exchanges_balances(),
            self.check_orders(),
            self.check_to_trade()
        ]

        group = asyncio.gather(*tasks)
        self.loop.run_until_complete(group)
        if self.ex_ev.is_set():
            self.log.info('=======CHECKER RUN EXIT EVENT=================')
            self.loop.stop()
            self.loop.close()
