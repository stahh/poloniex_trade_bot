from django import template
from frontend.models import ExchangeCoin, Pair, UserMainCoinPriority

register = template.Library()


@register.inclusion_tag('exchange_primary_coins.html')
def exchange_primary_coins(exchange):
    try:
        primary_coins = ExchangeCoin.objects.filter(exchange=exchange)
        active_coins = [x.main_coin for x in UserMainCoinPriority.objects.filter(
            user_exchange=exchange, is_active=True)]
        return {'primary_coins': primary_coins, 'active_coins': active_coins}
    except ExchangeCoin.DoesNotExist:
        return None


@register.inclusion_tag('primary_coin_pairs.html')
def primary_coin_pairs(primary_coin):
    try:
        pairs = Pair.objects.filter(main_coin=primary_coin.coin)
        return {'pairs': pairs}
    except Pair.DoesNotExist:
        return None
