from django.contrib import admin
from frontend import models


class UserOrderAdmin(admin.ModelAdmin):
    list_display = [field.name for field in models.UserOrder._meta.fields]
    list_filter = ['ue__exchange__name', 'order_type', 'ue__user__username']

    class Meta:
        model = models.UserOrder


class UserPairInline(admin.TabularInline):
    model = models.UserPair

    class Meta:
        model = models.UserPair


class ExchangeCoinAdmin(admin.ModelAdmin):
    search_fields = ['symbol', 'name']
    list_filter = ['exchange']

    class Meta:
        model = models.ExchangeCoin


class UserPairAdmin(admin.ModelAdmin):
    list_display = [field.name for field in models.UserPair._meta.fields]
    list_filter = ['user', 'pair__main_coin__exchange__name']

    class Meta:
        model = models.UserPair

#
# class CoinMarketCupCoinAdmin(admin.ModelAdmin):
#     search_fields = ['name', 'symbol']
#
#     def get_ordering(self, request):
#         return ['rank']
#
#     class Meta:
#         model = models.CoinMarketCupCoin


class PairAdmin(admin.ModelAdmin):
    search_fields = ['main_coin', 'second_coin']
    list_filter = ['main_coin__exchange__name']
    inlines = [UserPairInline]


class ToTradeAdmin(admin.ModelAdmin):
    list_display = [field.name for field in models.ToTrade._meta.fields]
    list_filter = ['user_pair__user_exchange', 'type', 'user_pair__pair']

    class Meta:
        model = models.ToTrade


class ExtremumAdmin(admin.ModelAdmin):
    list_display = [field.name for field in models.Extremum._meta.fields]

    class Meta:
        model = models.Extremum


class ExchangeTickerAdmin(admin.ModelAdmin):
    list_display = [field.name for field in models.ExchangeTicker._meta.fields]

    class Meta:
        model = models.ExchangeTicker


class UserBalancesAdmin(admin.ModelAdmin):
    list_display = [field.name for field in models.UserBalance._meta.fields]
    list_filter = ['ue']

    class Meta:
        model = models.UserBalance


admin.site.register(models.ExchangeCoin, ExchangeCoinAdmin)
admin.site.register(models.UserPair, UserPairAdmin)
admin.site.register(models.Pair, PairAdmin)
# admin.site.register(models.ExchangeMainCoin)
# admin.site.register(models.CoinMarketCupCoin, CoinMarketCupCoinAdmin)
admin.site.register(models.UserMainCoinPriority)
admin.site.register(models.ExchangeTicker, ExchangeTickerAdmin)
admin.site.register(models.ToTrade, ToTradeAdmin)
admin.site.register(models.UserOrder, UserOrderAdmin)
admin.site.register(models.UserCoinShare)
admin.site.register(models.Extremum, ExtremumAdmin)
admin.site.register(models.Exchanges)
admin.site.register(models.UserExchange)
admin.site.register(models.UserBalance, UserBalancesAdmin)
admin.site.register(models.Coin)
