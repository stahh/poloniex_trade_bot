from django import template
from frontend.models import ExchangeCoin

register = template.Library()


@register.inclusion_tag('coin_info.html')
def coin_info(symbol):
    try:
        coin = ExchangeCoin.objects.get(symbol=symbol)
    except ExchangeCoin.DoesNotExist:
        return None
    except ExchangeCoin.MultipleObjectsReturned:
        return None
    return {'coin': coin}
