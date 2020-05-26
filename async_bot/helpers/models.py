from sqlalchemy import (Column, Integer, String, Float, BigInteger, DateTime,
                        ForeignKey, Boolean)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

Base = declarative_base()


async def send_bulk(session, objects):
    try:
        session.bulk_save_objects(objects)
        session.commit()
    except Exception as e:
        raise e


async def create(session, model, **kwargs):
    try:
        instance = model(**kwargs)
        session.add(instance)
        session.commit()
        return instance
    except Exception as e:
        raise e


async def get_or_create(session, model, **kwargs):
    try:
        instance = session.query(model).filter_by(**kwargs).first()
        if instance:
            return instance
        else:
            instance = await create(session, model, **kwargs)
            return instance
    except Exception as e:
        raise e


async def get_first_by_filter(session, model, **kwargs):
    try:
        instance = session.query(model).filter_by(**kwargs).first()
        return instance
    except Exception as e:
        raise e


async def get_last_by_filter(session, model, **kwargs):
    instance = session.query(model).filter_by(**kwargs).last()
    return instance


async def get_by_filter(session, model, **kwargs):
    instance = session.query(model).filter_by(**kwargs).all()
    return instance


async def get_all(session, model):
    return session.query(model).all()


async def update_or_create(session, model, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        for k, v in kwargs.items():
            setattr(model, k, v)
        session.commit()
        return instance
    else:
        instance = await create(session, model, **kwargs)
    return instance


async def update_model(session, model, pk, data):
    try:
        instance = session.query(model).filter(model.id == pk)
        instance.update(data)
        session.commit()
    except Exception as e:
        raise e


class ExchangeTicker(Base):
    __tablename__ = 'exchange_tickers'
    id = Column(Integer, primary_key=True, autoincrement=True)
    exchange_id = Column(Integer, ForeignKey("exchanges.id"))
    pair_id = Column(Integer, ForeignKey('pair.id'))
    high = Column(Float(precision=15))
    last = Column(Float(precision=15))
    low = Column(Float(precision=15))
    bid = Column(Float(precision=15))
    ask = Column(Float(precision=15))
    base_volume = Column(Float(precision=15), nullable=True)
    percent_change = Column(Float(precision=8), nullable=True,
                            default=0)
    date_time = Column(DateTime, nullable=False)
    exchange = relationship("Exchanges",
                            foreign_keys=[exchange_id])
    pair = relationship("Pair",
                        foreign_keys=[pair_id])

    def __init__(self, exchange_id, pair_id, high, last, low, bid, ask,
                 base_volume, date_time, percent_change=None):
        self.exchange_id = exchange_id
        self.pair_id = pair_id
        self.high = high
        self.last = last
        self.low = low
        self.bid = bid
        self.ask = ask
        self.base_volume = base_volume
        self.percent_change = percent_change
        self.date_time = date_time

    def __repr__(self):
        return f'{self.exchange_id}: {self.pair_id}'


class Exchanges(Base):
    __tablename__ = 'exchanges'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255))
    info_frozen_key = Column(String(31))

    def __init__(self, name, info_frozen_key):
        self.name = name
        self.info_frozen_key = info_frozen_key

    def __repr__(self):
        return self.name


class User(Base):
    __tablename__ = 'auth_user'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(150), unique=True)
    password = Column(String(150))
    first_name = Column(String(30), nullable=True)
    last_name = Column(String(150), nullable=True)
    email = Column(String(150), nullable=True)
    is_staff = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    date_joined = Column(DateTime, default=datetime.now(timezone.utc))

    def __init__(self, username, first_name='', last_name='', email='',
                 is_staff=False, is_active=True):
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.is_staff = is_staff
        self.is_active = is_active

    def __repr__(self):
        return self.username


class UserExchange(Base):
    __tablename__ = 'user_exchange'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("auth_user.id"))
    exchange_id = Column(Integer, ForeignKey("exchanges.id"))
    apikey = Column(String(255))
    apisecret = Column(String(255))
    is_active = Column(Boolean, default=False)
    is_active_script = Column(Boolean, default=False)
    is_correct = Column(Boolean, default=True)
    total_btc = Column(Float(precision=8), default=0)
    total_usd = Column(Float(precision=8), default=0)
    coefficient_of_depth = Column(Integer, default=0)
    error = Column(String(255), default='')
    user = relationship("User", foreign_keys=[user_id])
    exchange = relationship("Exchanges", foreign_keys=[exchange_id])

    def __init__(self, user_id, exchange_id, apikey, apisecret, is_active,
                 is_active_script, is_correct, total_btc, total_usd,
                 coefficient_of_depth, error):
        self.user_id = user_id
        self.exchange_id = exchange_id
        self.apikey = apikey
        self.apisecret = apisecret
        self.is_active = is_active
        self.is_active_script = is_active_script
        self.is_correct = is_correct
        self.total_btc = total_btc
        self.total_usd = total_usd
        self.coefficient_of_depth = coefficient_of_depth
        self.error = error

    def __repr__(self):
        return f'{self.user.username}: {self.exchange.name}({self.id})'


class UserBalance(Base):
    __tablename__ = 'user_balance'
    id = Column(Integer, primary_key=True, autoincrement=True)
    ue_id = Column(Integer, ForeignKey("user_exchange.id"))
    coin = Column(String(10))
    total = Column(Float(precision=8), default=0)
    used = Column(Float(precision=8), default=0)
    free = Column(Float(precision=8), default=0)
    conversions = Column(String(255))
    btc_value = Column(Float(precision=8), default=0)
    last_update = Column(DateTime, default=datetime.now(timezone.utc))
    ue = relationship("UserExchange", foreign_keys=[ue_id])

    def __init__(self, ue_id, coin, total, used, free, conversions,
                 btc_value, last_update):
        self.ue_id = ue_id
        self.coin = coin
        self.total = total
        self.used = used
        self.free = free
        self.conversions = conversions
        self.btc_value = btc_value
        self.last_update = last_update

    def __repr__(self):
        return f'{self.ue.exchange.name} {self.ue.user.username} ' \
               f'{self.coin}: {self.total}'


class Coin(Base):
    __tablename__ = 'coin'
    id = Column(Integer, primary_key=True, autoincrement=False)
    short_name = Column(String(20), unique=True)
    full_name = Column(String(40), unique=True)
    fee = Column(Float, default=0.0)

    def __init__(self, id, short_name, full_name, fee):
        self.id = id
        self.short_name = short_name
        self.full_name = full_name
        self.fee = fee

    def __repr__(self):
        return f'{self.short_name}-{self.full_name}'


class ExchangeCoin(Base):
    __tablename__ = 'exchange_coin'
    id = Column(Integer, primary_key=True, autoincrement=True)
    exchange_id = Column(Integer, ForeignKey('exchanges.id'))
    symbol = Column(String(10))
    exchange = relationship("Exchanges", foreign_keys=[exchange_id])

    def __init__(self, exchange_id, symbol, rank=0):
        self.exchange_id = exchange_id
        self.symbol = symbol
        self.rank = rank

    def __repr__(self):
        return f'{self.exchange.name} {self.symbol}'


class UserPair(Base):
    __tablename__ = 'user_pair'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('auth_user.id'))
    user_exchange_id = Column(Integer, ForeignKey('user_exchange.id'))
    pair_id = Column(Integer, ForeignKey('pair.id'))
    rank = Column(Integer, default=1)
    rate_of_change = Column(Float, default=0)
    user = relationship("User", foreign_keys=[user_id])
    user_exchange = relationship("UserExchange", foreign_keys=[user_exchange_id])
    pair = relationship("Pair", foreign_keys=[pair_id])

    def __init__(self, user_id, user_exchange_id, pair_id, rank, rate_of_change):
        self.user_id = user_id
        self.user_exchange_id = user_exchange_id
        self.pair_id = pair_id
        self.rank = rank
        self.rate_of_change = rate_of_change

    def __repr__(self):
        return f'{self.user_exchange}: {self.name}'

    @property
    def name(self):
        return f'{self.main_coin}_{self.second_coin}'

    @property
    def main_coin(self):
        return self.pair.main_coin.symbol.upper()

    @property
    def second_coin(self):
        return self.pair.second_coin.symbol.upper()


class UserCoinShare(Base):
    __tablename__ = 'user_coin_share'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_exchange_id = Column(Integer, ForeignKey('user_exchange.id'))
    coin_id = Column(Integer, ForeignKey('exchange_coin.id'))
    share = Column(Float, default=0)
    coin = relationship("ExchangeCoin", foreign_keys=[coin_id])
    user_exchange = relationship("UserExchange", foreign_keys=[user_exchange_id])

    def __init__(self, user_exchange_id, coin_id, share):
        self.user_exchange_id = user_exchange_id
        self.coin_id = coin_id
        self.share = share

    def __repr__(self):
        return f'{self.user_exchange.exchange.name}: ' \
               f'{self.coin.symbol} {self.share}'

#
# class ExchangeMainCoin(Base):
#     __tablename__ = 'exchange_main_coin'
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     coin_id = Column(Integer, ForeignKey('exchange_coin.id'))
#     coin = relationship("ExchangeCoin", foreign_keys=[coin_id])
#
#     def __init__(self, coin_id):
#         self.coin_id = coin_id
#
#     def __repr__(self):
#         return f'{self.coin.exchange.name}: {self.coin.symbol}'


class Pair(Base):
    __tablename__ = 'pair'
    id = Column(Integer, primary_key=True, autoincrement=True)
    main_coin_id = Column(Integer, ForeignKey('exchange_coin.id'))
    second_coin_id = Column(Integer, ForeignKey('exchange_coin.id'))
    is_active = Column(Boolean, default=True)
    point_low_first = Column(Float(precision=15), default=0)
    point_low_last = Column(Float(precision=15), default=0)
    point_high_first = Column(Float(precision=15), default=0)
    point_high_last = Column(Float(precision=15), default=0)
    point_low_first_date = Column(DateTime, default=datetime.now(timezone.utc))
    point_low_last_date = Column(DateTime, default=datetime.now(timezone.utc))
    point_high_first_date = Column(DateTime, default=datetime.now(timezone.utc))
    point_high_last_date = Column(DateTime, default=datetime.now(timezone.utc))
    main_coin = relationship("ExchangeCoin", foreign_keys=[main_coin_id])
    second_coin = relationship("ExchangeCoin", foreign_keys=[second_coin_id])

    def __init__(self, main_coin_id, second_coin_id, is_active):
        self.main_coin_id = main_coin_id
        self.second_coin_id = second_coin_id
        self.is_active = is_active

    def __repr__(self):
        return f'{self.main_coin.exchange.name}: {self.name}'

    @property
    def name(self):
        return f'{self.main_coin.symbol.upper()}_' \
               f'{self.second_coin.symbol.upper()}'


class UserMainCoinPriority(Base):
    __tablename__ = 'user_main_coin_priority'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_exchange_id = Column(Integer, ForeignKey('user_exchange.id'))
    main_coin_id = Column(Integer, ForeignKey('exchange_coin.id'))
    priority = Column(Integer)
    is_active = Column(Boolean)
    user_exchange = relationship("UserExchange", foreign_keys=[user_exchange_id])
    main_coin = relationship("ExchangeCoin", foreign_keys=[main_coin_id])

    def __init__(self, user_exchange_id, main_coin_id, priority, is_active):
        self.user_exchange_id = user_exchange_id
        self.main_coin_id = main_coin_id
        self.priority = priority
        self.is_active = is_active

    def __repr__(self):
        return f'{self.user_exchange.exchange.name} {self.main_coin}'

#
# class CoinMarketCupCoin(Base):
#     __tablename__ = 'coin_market_cup_coin'
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     coin_market_id = Column(String(63), default='')
#     name = Column(String(63))
#     symbol = Column(String(15))
#     rank = Column(Integer)
#     price_usd = Column(Float)
#     volume_usd_24h = Column(Float, nullable=True)
#     available_supply = Column(Float, nullable=True)
#     total_supply = Column(Float, nullable=True)
#     percent_change_1h = Column(Float, nullable=True)
#     percent_change_24h = Column(Float, nullable=True)
#     percent_change_7d = Column(Float, nullable=True)
#
#     def __init__(self, coin_market_id, name, symbol, rank, price_usd,
#                  volume_usd_24h, available_supply, total_supply,
#                  percent_change_1h, percent_change_24h, percent_change_7d):
#         self.coin_market_id = coin_market_id
#         self.name = name
#         self.symbol = symbol
#         self.rank = rank
#         self.price_usd = price_usd
#         self.volume_usd_24h = volume_usd_24h
#         self.available_supply = available_supply
#         self.total_supply = total_supply
#         self.percent_change_1h = percent_change_1h
#         self.percent_change_24h = percent_change_24h
#         self.percent_change_7d = percent_change_7d
#
#     def __repr__(self):
#         return f'{self.name} {self.symbol}'
    #
    # def update(self, session, data):
    #     session.query(CoinMarketCupCoin).filter(
    #         CoinMarketCupCoin.id == self.id).update(data)
    #     session.commit()


class UserOrder(Base):
    __tablename__ = 'user_order'
    id = Column(Integer, primary_key=True, autoincrement=True)
    ue_id = Column(Integer, ForeignKey('user_exchange.id'))
    pair_id = Column(Integer, ForeignKey('pair.id'))
    order_type = Column(String(5))
    order_number = Column(BigInteger)
    main_coin_before_total = Column(Float, default=0.0)
    main_coin_before_free = Column(Float, default=0.0)
    main_coin_before_used = Column(Float, default=0.0)
    second_coin_before_total = Column(Float, default=0.0)
    second_coin_before_free = Column(Float, default=0.0)
    second_coin_before_used = Column(Float, default=0.0)
    main_coin_after_total = Column(Float, default=0.0)
    main_coin_after_free = Column(Float, default=0.0)
    main_coin_after_used = Column(Float, default=0.0)
    second_coin_after_total = Column(Float, default=0.0)
    second_coin_after_free = Column(Float, default=0.0)
    second_coin_after_used = Column(Float, default=0.0)
    price = Column(Float, default=0.0)
    amount = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    fee = Column(Float, default=0.0)
    fact_total = Column(Float, default=0.0)
    fact_fee = Column(Float, default=0.0)
    is_ok = Column(Boolean, default=True)
    interim_main_coin = Column(Float, default=0.0)
    date_created = Column(DateTime, default=datetime.now(timezone.utc))
    date_cancel = Column(DateTime, default=None, nullable=True)
    cancel_desc = Column(String(100), default='')
    date_updated = Column(DateTime, default=datetime.now(timezone.utc))
    to_close = Column(Boolean, default=False)
    is_fake = Column(Boolean, default=False)
    ue = relationship("UserExchange", foreign_keys=[ue_id])
    pair = relationship("Pair", foreign_keys=[pair_id])

    def __init__(self, ue_id, pair_id, order_type, order_number,
                 main_coin_before_total, main_coin_before_free,
                 main_coin_before_used, second_coin_before_total,
                 second_coin_before_free, second_coin_before_used,
                 price, amount, total, fee, interim_main_coin,
                 date_created=None, date_updated=None, cancel_desc=None):
        self.ue_id = ue_id
        self.pair_id = pair_id
        self.order_type = order_type
        self.order_number = order_number
        self.main_coin_before_total = main_coin_before_total
        self.main_coin_before_free = main_coin_before_free
        self.main_coin_before_used = main_coin_before_used
        self.second_coin_before_total = second_coin_before_total
        self.second_coin_before_free = second_coin_before_free
        self.second_coin_before_used = second_coin_before_used
        self.price = price
        self.amount = amount
        self.total = total
        self.fee = fee
        self.interim_main_coin = interim_main_coin
        self.date_created = date_created
        self.date_updated = date_updated
        self.cancel_desc = cancel_desc

    def __repr__(self):
        order = f'[Order num: {self.order_number}, ' \
                f'Order type: {self.order_type}, ' \
                f'Symbol: {self.pair.name}, ' \
                f'Amount: {self.amount}, ' \
                f'Price: {self.price},' \
                f'Total in BTC: {self.total}, ' \
                f'Date created: {self.date_created}, ' \
                f'Date updated: {self.date_updated}, ' \
                f'Date cancel: {self.date_cancel}]'
        return order


class ToTrade(Base):
    __tablename__ = 'to_trade'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_pair_id = Column(Integer, ForeignKey('user_pair.id'))
    type = Column(String(10))
    price = Column(Float)
    amount = Column(Float)
    total = Column(Float)
    total_f = Column(Float, default=0)
    fee = Column(Float)
    cause = Column(String(255))
    date_created = Column(DateTime, default=datetime.now())
    date_updated = Column(DateTime, default=datetime.now())
    user_pair = relationship("UserPair", foreign_keys=[user_pair_id])

    def __init__(self, user_pair_id, type, price, amount, total, total_f, fee,
                 cause, date_created=None, date_updated=None):
        self.user_pair_id = user_pair_id
        self.type = type
        self.price = price
        self.amount = amount
        self.total = total
        self.total_f = total_f
        self.fee = fee
        self.cause = cause
        self.date_created = date_created
        self.date_updated = date_updated

    def __repr__(self):
        to_trade = f'Pair: {self.user_pair.pair}, ' \
                   f'Type: {self.type}, ' \
                   f'Price: {self.price}, ' \
                   f'Amount: {self.amount}, ' \
                   f'Date created: {self.date_created}, ' \
                   f'Date updated: {self.date_updated}'
        return to_trade


class Extremum(Base):
    __tablename__ = 'extremum'
    id = Column(Integer, primary_key=True, autoincrement=True)
    pair_id = Column(Integer, ForeignKey('pair.id'))
    ext_type = Column(String(10))
    price = Column(Float)
    date = Column(DateTime, default=datetime.now(timezone.utc))
    pair = relationship("Pair", foreign_keys=[pair_id])

    def __init__(self, pair_id, ext_type, price, date):
        self.pair_id = pair_id
        self.ext_type = ext_type
        self.price = price
        self.date = date

    def __repr__(self):
        return f'{self.pair.name} {self.ext_type}: {str(self.date)}'


class ExchangeCharts(Base):
    __tablename__ = 'exchange_charts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    exchange_id = Column(Integer, ForeignKey("exchanges.id"))
    pair_id = Column(Integer, ForeignKey('pair.id'))
    period = Column(Integer)
    high = Column(Float(precision=15))
    low = Column(Float(precision=15))
    open = Column(Float(precision=15))
    close = Column(Float(precision=15))
    volume = Column(Float(precision=15))
    quote_volume = Column(Float(precision=8), nullable=True)
    weighted_average = Column(Float(precision=8), nullable=True,
                              default=0)
    date_time = Column(DateTime, nullable=False)
    exchange = relationship("Exchanges",
                            foreign_keys=[exchange_id])
    pair = relationship("Pair",
                        foreign_keys=[pair_id])

    def __init__(self, exchange_id, pair_id, period, high, low, open, close,
                 volume, quote_volume, weighted_average, date_time):
        self.exchange_id = exchange_id
        self.pair_id = pair_id
        self.period = period
        self.high = high
        self.low = low
        self.open = open
        self.close = close
        self.volume = volume
        self.quote_volume = quote_volume
        self.weighted_average = weighted_average
        self.date_time = date_time

    def __repr__(self):
        return f'Open:  {self.open}. Close: {self.close}. ' \
               f'High: {self.high}. Low: {self.low}'
