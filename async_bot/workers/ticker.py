import asyncio
import time
from datetime import datetime, timezone, timedelta
import datetime as dt
import re
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from frontend.settings import SQLALCHEMY_ENGINE, POLONIEX_API_KEY, \
    POLONIEX_API_SECRET, DAY_HISTORY
from async_bot.helpers.models import (
    Coin, UserExchange, ExchangeCoin, Exchanges, UserOrder,
    UserMainCoinPriority, Pair, ExchangeTicker, get_all, UserBalance,
    create, get_first_by_filter, update_model,
    ExchangeCharts, send_bulk)
from poloniex import Poloniex
from async_bot.helpers.utils import get_logger

engine = create_engine(SQLALCHEMY_ENGINE)
Session = sessionmaker(bind=engine)
session = Session()


class Ticker:

    def __init__(self, ex_ev):
        self.ex_ev = ex_ev
        self.log = None
        self.loop = asyncio.new_event_loop()
        self.polo = Poloniex()
        self.tickers = []
        self.bulk_size = 100

    async def eternity(self, timeout):
        while not self.ex_ev.is_set():
            await asyncio.sleep(timeout)

    @staticmethod
    async def calculate_points(charts):
        def walk(data):
            low = None
            low_ts = None
            high = None
            high_ts = None
            for char in data:
                if not low or char.get('low') < low:
                    low = char.get('low')
                    low_ts = char.get('date')
                if not high or char.get('high') > high:
                    high = char.get('high')
                    high_ts = char.get('date')
            return low, low_ts, high, high_ts

        return walk(charts[:30]), walk(charts[-20:])

    async def get_all_coins(self):
        response = self.polo.returnCurrencies()
        if 'error' not in response:
            for item in response:
                try:
                    data = {
                        'id': response[item]['id'],
                        'short_name': item,
                        'full_name': response[item]['name']
                    }
                    coin = await get_first_by_filter(session=session,
                                                     model=Coin,
                                                     **data)
                    if not coin:
                        data.update({'fee': response[item]['txFee']})
                        await create(session=session, model=Coin,
                                     **data)
                        await asyncio.sleep(0.01)
                except Exception as e:
                    self.log.error(f'Add coin {item} error: {repr(e)}')

    async def set_coin_priority(self, ue_id):
        ue = await get_first_by_filter(session=session, model=UserExchange,
                                       exchange_id=ue_id)
        coins = await get_all(session=session, model=ExchangeCoin)
        for coin in coins:
            try:
                coin_prior = await get_first_by_filter(
                    session=session, model=UserMainCoinPriority,
                    main_coin_id=coin.id)
                if not coin_prior:
                    data = {
                        'main_coin_id': coin.id,
                        'priority': 1,
                        'user_exchange_id': ue.id,
                        'is_active': True
                    }
                    await create(session=session,
                                 model=UserMainCoinPriority, **data)
            except Exception as e:
                self.log.error(f'Set coin priority Error: {e}')
                await asyncio.sleep(0.01)

    async def group_pull_exchanges(self, pair, item, exchange):
        quote, base = pair.split('_')
        coins = [quote, base]
        for coin in coins:
            try:
                data = {
                    'exchange_id': exchange.id,
                    'symbol': coin.lower()
                }

                instance = await get_first_by_filter(session=session,
                                                     model=ExchangeCoin,
                                                     **data)
                if not instance:
                    await create(session=session, model=ExchangeCoin,
                                 **data)
                    await asyncio.sleep(0.01)

            except Exception as e:
                self.log.error(f'Pull Exchange Error: {e}')
        # !!! AFTER ADD ALL COINS
        await asyncio.sleep(0.01)

        try:
            is_active = not bool(int(item.get('isFrozen', 0)))
            main_coin = await get_first_by_filter(
                session=session, model=ExchangeCoin,
                exchange_id=exchange.id,
                symbol=coins[0].lower())
            second_coin = await get_first_by_filter(
                session=session,
                model=ExchangeCoin,
                exchange_id=exchange.id,
                symbol=coins[1].lower())
            if main_coin and second_coin:
                old_pair = await get_first_by_filter(
                    session=session, model=Pair,
                    main_coin_id=main_coin.id,
                    second_coin_id=second_coin.id)
                if old_pair:
                    await update_model(session=session, model=Pair,
                                       pk=old_pair.id,
                                       data={'is_active': is_active})
                else:
                    data = {
                        'main_coin_id': main_coin.id,
                        'second_coin_id': second_coin.id,
                        'is_active': is_active
                    }
                    await create(session=session, model=Pair, **data)

        except Exception as e:
            self.log.error(f'Update/Create Pair Error: {e}')
            await asyncio.sleep(0.01)

    async def pull_exchanges(self):
        while not self.ex_ev.is_set():
            exchanges = await get_all(session=session, model=Exchanges)
            if not exchanges:
                await create(session=session, model=Exchanges,
                             name='Poloniex', info_frozen_key='')
                exchanges = await get_all(session=session, model=Exchanges)
            for exchange in exchanges:
                try:
                    ue = await get_first_by_filter(
                        session=session, model=UserExchange,
                        exchange_id=exchange.id)
                    markets = self.polo.returnTicker()
                    self.log.info('Start filling pairs')
                    [asyncio.ensure_future(
                        self.group_pull_exchanges(pair, item, exchange),
                        loop=self.loop)
                        for pair, item in markets.items()]
                    if ue:
                        await self.set_coin_priority(ue.id)
                except Exception as e:
                    self.log.error(f'Pull Exchanges Error: {e}')

            if self.ex_ev.is_set():
                break
            try:
                await asyncio.wait_for(self.eternity(10), timeout=3600.0)
            except asyncio.TimeoutError:
                ...

        self.log.info('=== Pull Exchanges(60s) Exited ===')

    async def group_pull_exchange_tickers(self, item, value, exchange):
        keys = ['high24hr', 'low24hr', 'highestBid', 'lowestAsk']
        if not any(value.get(x) for x in keys):
            return

        pair_str = re.match(r'([a-zA-Z0-9]+)_([a-zA-Z0-9]+)', item)
        if pair_str:
            try:
                main_coin = await get_first_by_filter(
                    session=session, model=ExchangeCoin,
                    symbol=pair_str.group(1))
                second_coin = await get_first_by_filter(
                    session=session, model=ExchangeCoin,
                    symbol=pair_str.group(2))
                pair = None
                if main_coin and second_coin:
                    pair = await get_first_by_filter(
                        session=session, model=Pair,
                        main_coin_id=main_coin.id,
                        second_coin_id=second_coin.id)
                if pair:
                    data = {
                        'exchange_id': exchange.id,
                        'pair_id': pair.id,
                        'high': value['high24hr'],
                        'low': value['low24hr'],
                        'bid': value['highestBid'],
                        'ask': value['lowestAsk'],
                        'base_volume': value['baseVolume'],
                        'last': value['last'],
                        'percent_change': value['percentChange'],
                        'date_time': datetime.now(timezone.utc),
                    }
                    self.tickers.append(ExchangeTicker(**data))
                # DELETE OLD TICKERS
                to_delete = session.query(ExchangeTicker).filter(
                    ExchangeTicker.date_time <=
                    datetime.now(timezone.utc) - dt.timedelta(
                        days=3))
                _ = to_delete.delete()
                session.commit()
                await asyncio.sleep(0.01)
            except Exception as e:
                self.log.error(f'Pair {pair_str}. Pull tickers error: {e}')

    async def pull_exchanges_tickers(self):
        while not self.ex_ev.is_set():
            if len(self.tickers) >= self.bulk_size:
                try:
                    await send_bulk(session, self.tickers)
                    self.tickers = []
                except Exception as e:
                    self.log.error(f'Create Bulk Error: {e}')

            exchanges = await get_all(session=session, model=Exchanges)
            if not exchanges:
                await create(session=session, model=Exchanges, name='Poloniex',
                             info_frozen_key='')
                exchanges = await get_all(session=session, model=Exchanges)

            for exchange in exchanges:
                try:
                    tickers = self.polo.returnTicker()
                    if tickers:
                        [asyncio.ensure_future(
                            self.group_pull_exchange_tickers(
                                item, value, exchange), loop=self.loop)
                            for item, value in tickers.items()]
                except Exception as e:
                    self.log.exception(f'Ticker Error:{e}')
                    continue

            if self.ex_ev.is_set():
                break
            try:
                await asyncio.wait_for(self.eternity(10), timeout=60.0)
            except asyncio.TimeoutError:
                ...

        self.log.info('=== Pull Exchanges Tickers(60s) Exited ===')

    async def group_pull_exchange_charts(self, pair, exchange_id):
        main_coin = pair.main_coin.symbol.upper()
        second_coin = pair.second_coin.symbol.upper()
        chart_data = []
        currency_pair = f'{main_coin}_{second_coin}'
        try:
            chart_data = self.polo.returnChartData(
                currencyPair=currency_pair,
                period=7200,
                start=int(datetime.timestamp(datetime.now().replace(
                    hour=0, minute=0, second=0, microsecond=0) -
                                             timedelta(hours=2 * 50))),
                end=int(time.time()))
        except:
            pass

        if not chart_data:
            return

        for chart in chart_data:
            try:
                if not await get_first_by_filter(
                        session=session, model=ExchangeCharts,
                        exchange_id=exchange_id, pair_id=pair.id,
                        date_time=datetime.fromtimestamp(
                            chart.get('date'), timezone.utc)):
                    await create(
                        session=session, model=ExchangeCharts,
                        exchange_id=exchange_id,
                        pair_id=pair.id,
                        period=86400,
                        high=chart.get('high'),
                        low=chart.get('low'),
                        open=chart.get('open'),
                        close=chart.get('close'),
                        volume=chart.get('volume'),
                        quote_volume=chart.get('quoteVolume'),
                        weighted_average=chart.get('weightedAverage'),
                        date_time=datetime.fromtimestamp(
                            chart.get('date'), timezone.utc))
                await asyncio.sleep(0.01)
            except Exception as e:
                self.log.exception(f'Bulk data error: {e}')
        try:
            first, last = await self.calculate_points(chart_data)
            data = {
                'point_low_first': first[0],
                'point_low_last': last[0],
                'point_high_first': first[2],
                'point_high_last': last[2],
                'point_low_first_date': datetime.fromtimestamp(
                    first[1], timezone.utc),
                'point_low_last_date': datetime.fromtimestamp(
                    last[1], timezone.utc),
                'point_high_first_date': datetime.fromtimestamp(
                    first[3], timezone.utc),
                'point_high_last_date': datetime.fromtimestamp(
                    last[3], timezone.utc)
            }
            await update_model(session=session, model=Pair, pk=pair.id,
                               data=data)
        except Exception as e:
            self.log.exception(f'Calculation of Points error: {e}')

    async def pull_exchanges_charts(self):
        while not self.ex_ev.is_set():
            if datetime.now().hour % 2 != 0:
                try:
                    await asyncio.wait_for(self.eternity(10), timeout=3600.0)
                except asyncio.TimeoutError:
                    ...
                continue

            exchanges = await get_all(session=session, model=Exchanges)
            if not exchanges:
                await create(session=session, model=Exchanges, name='Poloniex',
                             info_frozen_key='')
                exchanges = await get_all(session=session, model=Exchanges)

            for exchange in exchanges:
                try:
                    pairs = await get_all(session=session, model=Pair)
                    [asyncio.ensure_future(
                        self.group_pull_exchange_charts(
                            pair, exchange.id), loop=self.loop)
                        for pair in pairs]
                except Exception as e:
                    self.log.exception(f'Pull Chart Error:{e}')
                    continue

            if self.ex_ev.is_set():
                break
            try:
                await asyncio.wait_for(self.eternity(10), timeout=3600.0)
            except asyncio.TimeoutError:
                ...

        self.log.info('=== Pull Exchange Charts(3600s) Exited ===')

    async def fill_user_orders(self, pair_str, data):
        main_coin, second_coin = pair_str.split('_')
        main_coin = await get_first_by_filter(
            session=session, model=ExchangeCoin,
            symbol=main_coin.lower())
        second_coin = await get_first_by_filter(
            session=session, model=ExchangeCoin,
            symbol=second_coin.lower())
        pair = await get_first_by_filter(
            session=session, model=Pair,
            main_coin_id=main_coin.id,
            second_coin_id=second_coin.id)
        exchange = await get_first_by_filter(session=session, model=Exchanges,
                                             name='poloniex')
        ue = await get_first_by_filter(session=session, model=UserExchange,
                                       exchange_id=exchange.id)
        for order_data in data:
            try:
                data = {
                    'order_number': order_data['orderNumber'],
                    'pair_id': pair.id,
                }
                order = await get_first_by_filter(session=session,
                                                  model=UserOrder,
                                                  **data)
                main_coin_balance = await get_first_by_filter(
                    session=session, model=UserBalance, ue_id=ue.id,
                    coin=main_coin.symbol)
                second_coin_balance = await get_first_by_filter(
                    session=session, model=UserBalance, ue_id=ue.id,
                    coin=second_coin.symbol)
                if not order:
                    data = {
                        'ue_id': ue.id,
                        'pair_id': pair.id,
                        'order_type': order_data['type'],
                        'order_number': order_data['orderNumber'],
                        'price': order_data['rate'],
                        'amount': order_data['amount'],
                        'total': order_data['total'],
                        'date_created': order_data['date'],
                        'interim_main_coin': 0,
                        'main_coin_before_total': main_coin_balance.total,
                        'main_coin_before_free': main_coin_balance.free,
                        'main_coin_before_used': main_coin_balance.used,
                        'second_coin_before_total': second_coin_balance.total,
                        'second_coin_before_free': second_coin_balance.free,
                        'second_coin_before_used': second_coin_balance.used,
                        'date_updated': order_data['date'],
                        'fee': order_data['fee'],
                        'cancel_desc': 'Worked'
                    }
                    await create(session=session, model=UserOrder,
                                 **data)
                    await asyncio.sleep(0.01)
            except Exception as e:
                self.log.error(f'Add order {order_data} error: {repr(e)}')

    async def pull_trade_history(self):
        try:
            start = datetime.now(timezone.utc) - dt.timedelta(days=DAY_HISTORY)
            end = time.time()
            history = Poloniex(
                POLONIEX_API_KEY,
                POLONIEX_API_SECRET).returnTradeHistory(
                start=start.timestamp(), end=end)
            [asyncio.ensure_future(
                self.fill_user_orders(pair, data), loop=self.loop)
                for pair, data in history.items()]
        except Exception as e:
            self.log.error(f'pull_trade_history Error: {e}')

    def run(self):
        self.log = get_logger('ticker')
        self.log.info('Start Ticker')

        asyncio.set_event_loop(self.loop)
        tasks = [self.get_all_coins(), self.pull_trade_history(),
                 self.pull_exchanges(), self.pull_exchanges_tickers(),
                 self.pull_exchanges_charts()]

        group = asyncio.gather(*tasks)
        self.loop.run_until_complete(group)
        if self.ex_ev.is_set():
            self.log.info('=======TICKER RUN EXIT EVENT=============')
            self.loop.stop()
            self.loop.close()
