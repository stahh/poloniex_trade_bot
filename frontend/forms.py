from django.forms import ModelForm
from frontend.models import UserExchange


class UserExchangesForm(ModelForm):
    class Meta:
        model = UserExchange
        fields = ['exchange', 'apikey', 'apisecret']
