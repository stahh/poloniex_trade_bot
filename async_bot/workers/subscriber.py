import json
import re
import time
from collections import OrderedDict
import asyncio
import jsonpickle
import websockets
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

from frontend.settings import (
    UNIDIRECTIONAL_COUNT, DIRECTIONS_COUNT, API_LINK, SUBSCRIBE_COMMAND,
    TICKER_SUBSCRIBE)
from async_bot.helpers.models import (
    Exchanges, ExchangeCoin,Pair, Extremum, UserPair, UserOrder,
    create, get_first_by_filter, update_model)
from async_bot.helpers.calculator import calculate_order_for_user, is_need_sell
from async_bot.helpers.order_book import OrderBooks
from poloniex import Poloniex
from frontend.settings import SQLALCHEMY_ENGINE
from async_bot.helpers.telegramm_bot import send_telegram
from async_bot.helpers.utils import get_logger

engine = create_engine(SQLALCHEMY_ENGINE)
Session = sessionmaker(bind=engine)
session = Session()


class Ticker:
    def __init__(self, pair_id, pair, last, high, low, date):
        self.pair = pair
        self.pair_id = pair_id
        self.last = last
        self.high = high
        self.low = low
        self.date = date
        self.prev_last = None
        self.prev_date = None
        self.prev_high = None
        self.prev_low = None


class TickerList:
    """
    Container for tickers
    """

    def __init__(self, log):
        self.tickers_by_name = {}
        self.tickers_by_id = {}
        self.log = log

    async def get_ticker_by_id(self, pair_id):
        return self.tickers_by_id.get(pair_id)

    async def get_ticker_by_name(self, pair_name):
        return self.tickers_by_name.get(pair_name)

    async def new_ticker(self, pair, pair_id, last, high, low, date):
        try:
            ticker = await self.get_ticker_by_id(pair_id)
            if ticker is not None:
                ticker.prev_last = ticker.last
                ticker.prev_date = ticker.date
                ticker.prev_high = ticker.high
                ticker.prev_low = ticker.low
                ticker.last = last
                ticker.date = date
                ticker.high = high
                ticker.low = low
            else:
                ticker = Ticker(pair_id, pair, last, high, low, date)
                self.tickers_by_id[pair_id] = ticker
                self.tickers_by_name[pair] = ticker
            return ticker
        except Exception as e:
            self.log.exception(e)


class Subscriber:
    def __init__(self, ex_ev):
        self.ex_ev = ex_ev
        self.log = None
        self.loop = asyncio.new_event_loop()
        self.polo = Poloniex()
        self._tickers_list = {}
        self._markets_list = []
        self._tickers_id = {}
        self._last_seq_dic = {}
        self.order_books = OrderBooks()
        self.ticker_list = None
        self.directions = {}
        self.extremums = {}
        self.exchange = None

    async def cancel_user_orders(self, marker_id, order_type):
        try:
            user_order = await get_first_by_filter(session=session,
                                                   model=UserOrder,
                                                   pair_id=marker_id,
                                                   order_type=order_type,
                                                   date_cancel=None)
            if user_order:
                await update_model(session=session, model=UserOrder,
                                   pk=user_order.id, data={'to_close': True})
        except Exception as e:
            self.log.error(f'Cancel user order error: {e}')

    async def fill_pairs(self):
        try:
            tickers_data = self.polo.returnTicker()
            for item, data in tickers_data.items():
                self._tickers_id[data['id']] = item
                self._markets_list.append(item)
                pair_str = re.match(r'([a-zA-Z0-9]+)_([a-zA-Z0-9]+)', item)
                if pair_str:
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
                        self._tickers_list[data['id']] = pair.id

            self.exchange = await get_first_by_filter(
                session=session, model=Exchanges, name='poloniex')
        except Exception as e:
            self.log.exception(f'Method fill_pairs Error: {e}')

    async def add_market_direction(self, pair_id, direction, timestamp):
        # DIRECTION => {pair_id: [[direction, timestamp]]}
        try:
            if pair_id in self.directions:
                if len(self.directions[pair_id]) >= DIRECTIONS_COUNT:
                    self.directions[pair_id].pop(0)
                self.directions[pair_id].append([direction, timestamp])
            else:
                self.directions.update({pair_id: [[direction, timestamp]]})
        except Exception as e:
            self.log.exception(f'Method add_market_direction Error: {e}')

    async def check_directions_is_extremum(self, pair_id):
        # DIRECTION => {pair_id: [[direction, timestamp]]}
        try:
            if pair_id in self.directions:
                if len(self.directions[pair_id]) < DIRECTIONS_COUNT:
                    return False
                else:
                    sum_first_n_elem = sum(
                        [x[0] for x in
                         self.directions[pair_id][:UNIDIRECTIONAL_COUNT]])
                    sum_last_n_elem = sum(
                        [x[0] for x in
                         self.directions[pair_id][UNIDIRECTIONAL_COUNT:]])
                    if sum_first_n_elem >= UNIDIRECTIONAL_COUNT - 1 \
                            and sum_last_n_elem == 0:
                        return 'buy'
                    elif sum_first_n_elem <= 1 and sum_last_n_elem == \
                            DIRECTIONS_COUNT - \
                            UNIDIRECTIONAL_COUNT:
                        return 'sell'
                    else:
                        return False
            else:
                return False
        except Exception as e:
            self.log.exception(f'Method check_directions_is_extremum '
                               f'Error: {e}')

    async def check_extremum(self, pair_id, date, ext_type, last, market_id):
        # EXTREMUM => pair_id: [date, ext_type(buy/sell), last]
        try:
            extremum = self.extremums.get(pair_id)
            if extremum:
                _ext_type, _last = extremum[1:]
                if ext_type == _ext_type:
                    if ext_type == 'buy':
                        if last <= _last:
                            return False
                        else:
                            await self.cancel_user_orders(
                                marker_id=market_id, order_type='sell')
                            self.extremums.update(
                                {pair_id: [date, ext_type, last]})
                            return True
                    elif ext_type == 'sell':
                        if last >= _last:
                            return False
                        else:
                            await self.cancel_user_orders(
                                marker_id=market_id, order_type='buy')
                            self.extremums.update(
                                {pair_id: [date, ext_type, last]})
                            return True
                else:
                    if _ext_type == 'buy':
                        if _last < last:
                            return False
                        else:
                            self.extremums.update(
                                {pair_id: [date, ext_type, last]})
                            return True
                    elif _ext_type == 'sell':
                        if _last > last:
                            return False
                        else:
                            self.extremums.update(
                                {pair_id: [date, ext_type, last]})
                            return True
            else:
                self.extremums.update({pair_id: [date, ext_type, last]})
                return True
        except Exception as e:
            self.log.exception(f'Method check_extremum Error: {e}')

    async def get_websocket(self):
        websocket = await websockets.connect(API_LINK, loop=self.loop)
        await websocket.send(SUBSCRIBE_COMMAND.replace(
            '$', str(TICKER_SUBSCRIBE)))
        for ticker in self._markets_list:
            req = SUBSCRIBE_COMMAND.replace(
                '$', '\"' + ticker + '\"')
            await websocket.send(req)
        return websocket

    async def subscribe(self):
        try:
            websocket = await self.get_websocket()
            # now parse received data
            t = time.time()
            while not self.ex_ev.is_set():
                # if we did not get data for 60sec - re-connect and update t
                if time.time() - t > 60.0:
                    self.log.error(
                        'Websocket Timeout. Trying to reconnect.')
                    try:
                        await websocket.close()
                    except:
                        ...
                    websocket = await self.get_websocket()
                    t = time.time()
                    continue
                if not websocket.open:
                    self.log.error(
                        'Websocket NOT connected. Trying to reconnect.')
                    try:
                        await websocket.close()
                    except:
                        ...
                    websocket = await self.get_websocket()
                    continue
                try:
                    message = await websocket.recv()
                except websockets.ConnectionClosed:
                    self.log.error(
                        'Websocket Connection closed. Reconnect')
                    try:
                        await websocket.close()
                    except:
                        ...
                    websocket = await self.get_websocket()
                    continue

                data = json.loads(message, object_pairs_hook=OrderedDict)
                if 'error' in data:
                    self.log.error(f'Error getting websocket data: {data}')
                    continue
                if len(data) < 2:
                    self.log.error(
                        'Short message received: {}'.format(data))
                    continue

                if data[0] == 1010 or data[1] == 1:
                    # this means heartbeat
                    continue
                if data[1] == 0:
                    # this means the subscription is failure
                    raise Exception(
                        f'Subscription Failed message received: {data}')

                if data[0] == TICKER_SUBSCRIBE:
                    t = time.time()
                    values = data[2]

                    if values[0] not in self._tickers_list:
                        continue

                    ticker_id_int = values[0]
                    ticker_bid = values[3]
                    ticker_ask = values[2]
                    pair_id = self._tickers_list[ticker_id_int]

                    pair = await get_first_by_filter(
                        session=session, model=Pair, id=pair_id)
                    user_pair = None
                    if pair:
                        user_pair = await get_first_by_filter(
                            session=session, model=UserPair,
                            pair_id=pair.id,
                            user_exchange_id=self.exchange.id)

                    if not user_pair:
                        continue

                    ct = await self.ticker_list.new_ticker(
                        pair_id=self._tickers_id[ticker_id_int],
                        pair=self._tickers_id[ticker_id_int],
                        last=values[1],
                        high=ticker_bid,
                        low=ticker_ask,
                        date=time.time())

                    if ct.last is None or ct.prev_last is None:
                        continue
                    extremum = False
                    if ct.low > ct.prev_low and ct.high > ct.prev_high:
                        await self.add_market_direction(
                            ct.pair, 1, ct.date)
                        extremum = await self.check_directions_is_extremum(
                            ct.pair)
                    elif ct.low < ct.prev_low and ct.high < ct.prev_high:
                        await self.add_market_direction(
                            ct.pair, 0, ct.date)
                        extremum = await self.check_directions_is_extremum(
                            ct.pair)

                    market = await self.order_books.get_market_by_id(
                        ticker_id_int)
                    if not market:
                        continue

                    if extremum:
                        is_ext = await self.check_extremum(
                            ct.pair, ct.date, extremum, ct.last, pair_id)
                        if not is_ext:
                            continue

                        self.log.info(
                            f'Pair: {ct.pair,}, found extremum: {extremum}, '
                            f'time {datetime.now(timezone.utc)}')

                        await create(
                            session=session,
                            model=Extremum,
                            pair_id=pair_id,
                            ext_type='buy' if
                            extremum == 'sell' else 'sell',
                            price=ct.last,
                            date=datetime.now(timezone.utc))

                        if extremum == 'sell':

                            args_buy = {'pair': pair_id,
                                        'bids': market.bids[:200],
                                        'asks': market.asks[:200],
                                        'ticker': jsonpickle.encode(
                                            self.ticker_list)}
                            self.log.info(f'Sending to buy: {pair}')
                            await calculate_order_for_user(
                                user_pair, args_buy, 'buy', self.polo)
                        elif extremum == 'buy':
                            args_sell = {'pair': pair_id,
                                         'asks': market.asks[:200],
                                         'bids': market.bids[:200]}
                            self.log.info(f'Sending to sell: {pair}')
                            await calculate_order_for_user(
                                user_pair, args_sell, 'sell', self.polo)
                    else:
                        if await is_need_sell(user_pair, ticker_ask,
                                              market.asks[:200]):
                            args_sell = {'pair': pair_id,
                                         'asks': market.asks[:200],
                                         'bids': market.bids[:200]}
                            self.log.info(f'Sending to buy without '
                                          f'extremum: {pair}')
                            await calculate_order_for_user(
                                user_pair, args_sell, 'sell', self.polo)
                else:
                    # ORDER BOOK
                    ticker_name = self._tickers_id[data[0]]
                    seq = data[1]
                    for up_data in data[2]:
                        # it means this is snapshot
                        if up_data[0] == 'i':
                            # UPDATE[1]['currencyPair'] is the ticker name
                            self._last_seq_dic[ticker_name] = seq
                            asks = [[price, size] for price, size
                                    in up_data[1]['orderBook'][0].items()]

                            bids = [[price, size] for price, size
                                    in up_data[1]['orderBook'][1].items()]

                            await self.order_books.add_market(
                                ticker_id=data[0], ticker_name=ticker_name,
                                asks=asks, bids=bids)
                        # it means add or change or remove
                        elif up_data[0] == 'o':
                            if self._last_seq_dic[ticker_name] + 1 != seq:
                                self.log.error(
                                    'Problem with seq number prev_seq={},'
                                    'message={}'.format(
                                        self._last_seq_dic[ticker_name],
                                        message))
                                await asyncio.sleep(0.001)
                                continue

                            price = up_data[2]
                            side = 'bid' if up_data[1] == 1 else 'ask'
                            size = up_data[3]
                            market = \
                                await self.order_books.get_market_by_id(
                                    data[0])
                            if market is not None:
                                # this mean remove
                                if float(size) == 0.0:
                                    try:
                                        await market.remove_item(
                                            side=side, price=str(price))
                                    except Exception as e:
                                        self.log.exception(
                                            f"Error remove item from "
                                            f"market: {e}")
                                # it means add or change
                                else:
                                    try:
                                        await market.add_or_change(
                                            side=side, price=price,
                                            size=size)
                                    except Exception as e:
                                        self.log.exception(
                                            f"Error addition item to "
                                            f"market: {e}")

                    self._last_seq_dic[ticker_name] = seq
                await asyncio.sleep(0.001)
            await websocket.close()
        except Exception as e:
            self.log.exception(f'Subscriber Error: {e}')
            send_telegram(
                title='ERROR',
                text=f'Subscriber Error: {e}')
        if self.ex_ev.is_set():
            return

    def run(self):
        self.log = get_logger('subscriber')
        self.ticker_list = TickerList(self.log)
        self.log.info('Start Subscriber')
        asyncio.set_event_loop(self.loop)
        tasks = [
            self.fill_pairs(),
            self.subscribe(),
        ]

        group = asyncio.gather(*tasks)
        self.loop.run_until_complete(group)
        if self.ex_ev.is_set():
            self.log.info(
                '=======SUBSCRIBER RUN EXIT EVENT===========')
            self.loop.stop()
            self.loop.close()
