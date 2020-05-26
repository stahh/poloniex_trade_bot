from django.contrib.auth.models import User
from django.db import models
from datetime import datetime, timezone


class Exchanges(models.Model):
    name = models.CharField(max_length=255)
    info_frozen_key = models.CharField(max_length=31)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Биржа"
        verbose_name_plural = "Биржи"
        db_table = "exchanges"


class UserExchange(models.Model):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    exchange = models.ForeignKey(Exchanges, on_delete=models.DO_NOTHING)
    apikey = models.CharField(max_length=127)
    apisecret = models.CharField(max_length=255)
    is_active = models.BooleanField(default=False)
    is_active_script = models.BooleanField(default=False)
    is_correct = models.BooleanField(default=True)
    total_btc = models.FloatField()
    total_usd = models.FloatField(default=0)
    coefficient_of_depth = models.IntegerField(default=0)
    error = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f'{self.user.username}: {self.exchange.name} ({self.id})'

    class Meta:
        verbose_name = "Биржа пользователя"
        verbose_name_plural = "Биржи пользователей"
        db_table = "user_exchange"


class ExchangeCoin(models.Model):
    exchange = models.ForeignKey(Exchanges, on_delete=models.DO_NOTHING)
    symbol = models.CharField(max_length=10)

    def __str__(self):
        return self.exchange.name + ' ' + self.symbol

    class Meta:
        verbose_name = "Монета биржи"
        verbose_name_plural = "Монеты биржи"
        db_table = "exchange_coin"


class Pair(models.Model):
    main_coin = models.ForeignKey(
        ExchangeCoin, on_delete=models.DO_NOTHING,
        related_name='%(class)s_main_coin')
    second_coin = models.ForeignKey(
        ExchangeCoin, on_delete=models.DO_NOTHING,
        related_name='%(class)s_second_coin')
    is_active = models.BooleanField(default=True)
    point_low_first = models.DecimalField(
        max_digits=30, decimal_places=15, default=0)
    point_low_last = models.DecimalField(
        max_digits=30, decimal_places=15, default=0)
    point_high_first = models.DecimalField(
        max_digits=30, decimal_places=15, default=0)
    point_high_last = models.DecimalField(
        max_digits=30, decimal_places=15, default=0)
    point_low_first_date = models.DateTimeField(
        default=datetime.now(timezone.utc))
    point_low_last_date = models.DateTimeField(
        default=datetime.now(timezone.utc))
    point_high_first_date = models.DateTimeField(
        default=datetime.now(timezone.utc))
    point_high_last_date = models.DateTimeField(
        default=datetime.now(timezone.utc))

    def __str__(self):
        return f'{self.main_coin.exchange.name}: ' \
               f'{self.main_coin.symbol.upper()}_' \
               f'{self.second_coin.symbol.upper()}'

    class Meta:
        verbose_name = "Пара"
        verbose_name_plural = "Пары"
        db_table = 'pair'


class ExchangeTicker(models.Model):
    exchange = models.ForeignKey(
        Exchanges, on_delete=models.DO_NOTHING, default=1)
    pair = models.ForeignKey(Pair, on_delete=models.DO_NOTHING, default=1)
    high = models.DecimalField(max_digits=30, decimal_places=15)
    last = models.DecimalField(max_digits=30, decimal_places=15)
    low = models.DecimalField(max_digits=30, decimal_places=15)
    bid = models.DecimalField(max_digits=30, decimal_places=15)
    ask = models.DecimalField(max_digits=30, decimal_places=15)
    base_volume = models.DecimalField(
        max_digits=30, decimal_places=15, null=True, blank=True)
    percent_change = models.DecimalField(
        max_digits=10, decimal_places=8, default=0)
    date_time = models.DateTimeField(blank=False, null=False)

    def __str__(self):
        return f'{self.exchange_id}: {self.pair_id}'

    class Meta:
        verbose_name = 'Данные тикера'
        verbose_name_plural = 'Данные тикеров'
        db_table = 'exchange_tickers'


class UserPair(models.Model):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    user_exchange = models.ForeignKey(
        UserExchange, on_delete=models.DO_NOTHING)
    pair = models.ForeignKey(Pair, on_delete=models.DO_NOTHING)
    rank = models.PositiveIntegerField(default=1)
    rate_of_change = models.FloatField(default=0)

    class Meta:
        verbose_name = "Пара пользователя"
        verbose_name_plural = "Пары пользователей"
        db_table = 'user_pair'

    def __str__(self):
        return f'{self.user_exchange}: ' \
               f'{self.pair.main_coin.symbol.upper()}_' \
               f'{self.pair.second_coin.symbol.upper()}'


class UserCoinShare(models.Model):
    user_exchange = models.ForeignKey(
        UserExchange, on_delete=models.DO_NOTHING)
    coin = models.ForeignKey(ExchangeCoin, on_delete=models.DO_NOTHING)
    share = models.FloatField(default=0)

    def __str__(self):
        return f'{self.user_exchange.exchange.name}: ' \
               f'{self.coin.symbol} {self.share}'

    class Meta:
        verbose_name = 'Доля валюты'
        verbose_name_plural = 'Доли валют'
        db_table = 'user_coin_share'

#
# class ExchangeMainCoin(models.Model):
#     coin = models.ForeignKey(ExchangeCoin, on_delete=models.DO_NOTHING)
#
#     def __str__(self):
#         return f'{self.coin.exchange.name}: {self.coin.symbol}'
#
#     class Meta:
#         verbose_name = "Главная монета биржи"
#         verbose_name_plural = "Главные монеты биржи"
#         db_table = 'exchange_main_coin'


class UserMainCoinPriority(models.Model):
    user_exchange = models.ForeignKey(
        UserExchange, on_delete=models.DO_NOTHING)
    main_coin = models.ForeignKey(ExchangeCoin, on_delete=models.DO_NOTHING)
    priority = models.PositiveIntegerField()
    is_active = models.BooleanField()

    def __str__(self):
        return f'{self.user_exchange.exchange.name} {self.main_coin}'

    class Meta:
        verbose_name_plural = 'Главные монеты пользователей'
        verbose_name = 'Главная монета пользователя'
        db_table = 'user_main_coin_priority'


# class CoinMarketCupCoin(models.Model):
#     coin_market_id = models.CharField(
#         max_length=63, verbose_name="Внутренее имя", default='')
#     name = models.CharField(max_length=63, verbose_name="Имя")
#     symbol = models.CharField(max_length=15, verbose_name="Аббр")
#     rank = models.PositiveIntegerField()
#     price_usd = models.FloatField(verbose_name="Цена в USD")
#     volume_usd_24h = models.FloatField(null=True)
#     available_supply = models.FloatField(null=True)
#     total_supply = models.FloatField(null=True)
#     percent_change_1h = models.FloatField(null=True)
#     percent_change_24h = models.FloatField(null=True)
#     percent_change_7d = models.FloatField(null=True)
#
#     class Meta:
#         verbose_name = 'Монета CoinMarketCup'
#         verbose_name_plural = 'Монеты CoinMarketCup'
#         db_table = 'coin_market_cup_coin'
#
#     def __str__(self):
#         return f'{self.name} {self.symbol}'


class UserOrder(models.Model):
    ue = models.ForeignKey(UserExchange, on_delete=models.DO_NOTHING)
    pair = models.ForeignKey(Pair, on_delete=models.DO_NOTHING)
    order_type = models.CharField(max_length=5)
    order_number = models.BigIntegerField()
    main_coin_before_total = models.FloatField(default=0.0)
    main_coin_before_free = models.FloatField(default=0.0)
    main_coin_before_used = models.FloatField(default=0.0)
    second_coin_before_total = models.FloatField(default=0.0)
    second_coin_before_free = models.FloatField(default=0.0)
    second_coin_before_used = models.FloatField(default=0.0)
    main_coin_after_total = models.FloatField(default=0.0)
    main_coin_after_free = models.FloatField(default=0.0)
    main_coin_after_used = models.FloatField(default=0.0)
    second_coin_after_total = models.FloatField(default=0.0)
    second_coin_after_free = models.FloatField(default=0.0)
    second_coin_after_used = models.FloatField(default=0.0)
    price = models.FloatField(default=0.0)
    amount = models.FloatField(default=0.0)
    total = models.FloatField(default=0.0)
    fee = models.FloatField(default=0.0)
    fact_total = models.FloatField(default=0.0)
    fact_fee = models.FloatField(default=0.0)
    is_ok = models.NullBooleanField(default=None, blank=True, null=True)
    interim_main_coin = models.FloatField(default=0.0)
    date_created = models.DateTimeField(auto_now_add=True)
    date_cancel = models.DateTimeField(default=None, blank=True, null=True)
    cancel_desc = models.CharField(max_length=100, default='')
    date_updated = models.DateTimeField(auto_now=True)
    to_close = models.BooleanField(default=False)
    is_fake = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.ue.user.username} {self.ue.exchange.name}: ' \
               f'{self.order_type} {self.pair.main_coin.symbol.upper()}_' \
               f'{self.pair.second_coin.symbol.upper()}'

    class Meta:
        verbose_name_plural = 'Ордера пользователей'
        verbose_name = 'Ордер пользователя'
        ordering = ('date_created',)
        db_table = 'user_order'


class ToTrade(models.Model):
    user_pair = models.ForeignKey(
        UserPair, blank=False, null=False, on_delete=models.DO_NOTHING)
    type = models.CharField(max_length=10, blank=False, null=False)
    price = models.FloatField(blank=False, null=False)
    amount = models.FloatField(blank=False, null=False)
    total = models.FloatField(blank=False, null=False)
    total_f = models.FloatField(blank=False, null=False, default=0)
    fee = models.FloatField(blank=False, null=False)
    cause = models.CharField(max_length=255)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user_pair.pair} {self.type}'

    class Meta:
        verbose_name = 'Пара готовая к торговле'
        verbose_name_plural = 'Пары готовые к торговле'
        db_table = 'to_trade'


class Extremum(models.Model):
    pair = models.ForeignKey(Pair, on_delete=models.DO_NOTHING)
    ext_type = models.CharField(max_length=10)
    price = models.FloatField()
    date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Экстремум'
        verbose_name_plural = 'Экстремумы'
        db_table = 'extremum'

    def __str__(self):
        return f'{self.pair.main_coin.symbol.upper()}_' \
               f'{self.pair.second_coin.symbol.upper()} ' \
               f'{self.ext_typ}: {self.date}'


class UserBalance(models.Model):
    ue = models.ForeignKey(UserExchange, on_delete=models.DO_NOTHING)
    coin = models.CharField(max_length=10)
    total = models.FloatField(default=0)
    used = models.FloatField(default=0)
    free = models.FloatField(default=0)
    conversions = models.CharField(max_length=255)
    btc_value = models.FloatField(default=0)
    last_update = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.ue.exchange.name} {self.ue.user.username} ' \
               f'{self.coin}: {self.total}'

    class Meta:
        verbose_name = "Баланс пользователя"
        verbose_name_plural = "Балансы пользователей"
        db_table = 'user_balance'


class Coin(models.Model):
    id = models.IntegerField(primary_key=True, auto_created=False)
    short_name = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=40, unique=True)
    fee = models.DecimalField(max_digits=30, decimal_places=15, default=0.1)

    def __str__(self):
        return f'{self.short_name}-{self.full_name}'

    class Meta:
        verbose_name = 'Криптовалюта'
        verbose_name_plural = 'Криптовалюты'
        db_table = 'coin'


class ExchangeCharts(models.Model):
    pair = models.ForeignKey(Pair, on_delete=models.DO_NOTHING, default=1)
    exchange = models.ForeignKey(
        Exchanges, on_delete=models.DO_NOTHING, default=1)
    period = models.IntegerField()
    high = models.DecimalField(max_digits=30, decimal_places=15)
    low = models.DecimalField(max_digits=30, decimal_places=15)
    open = models.DecimalField(max_digits=30, decimal_places=15)
    close = models.DecimalField(max_digits=30, decimal_places=15)
    volume = models.DecimalField(
        max_digits=30, decimal_places=15, null=True, blank=True)
    quote_volume = models.DecimalField(
        max_digits=30, decimal_places=15, default=0)
    weighted_average = models.DecimalField(
        max_digits=30, decimal_places=15, default=0)
    date_time = models.DateTimeField(blank=False, null=False)

    class Meta:
        verbose_name = 'Бары'
        verbose_name_plural = 'Бары'
        db_table = 'exchange_charts'
