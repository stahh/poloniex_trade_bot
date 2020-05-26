from django import template
from frontend.models import UserExchange
import requests

register = template.Library()


@register.filter
def get_user_summaries_usd(user):
    btc_total = float(0)
    print(f'USER {user}')
    exchanges = UserExchange.objects.filter(user=user)
    if exchanges is not None:
        for exchange in exchanges:
            btc_total += float(exchange.total_btc)
    if btc_total > 0:
        i = 5
        while i > 0:
            try:
                btc_price = requests.get(
                    'https://api.hitbtc.com/api/2/public/ticker/btcusd').json()
                usd_total = float(btc_total) * float(btc_price['ask'])
                return usd_total
            except:
                pass
            i -= 1
    return 0


@register.filter
def get_user_summaries_btc(user):
    btc_total = float(0)
    exchanges = UserExchange.objects.filter(user=user)
    if exchanges is not None:
        for exchange in exchanges:
            btc_total += float(exchange.total_btc)
    return btc_total


@register.filter
def as_percent_of(part, whole):
    try:
        return float(part) / whole * 100
    except (ValueError, ZeroDivisionError):
        return 0
