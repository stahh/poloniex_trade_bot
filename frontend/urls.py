"""djangoTrade URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls import url, include
from django.conf.urls.static import static
from django.contrib import admin
from frontend import views
from allauth import urls as allauth_urls
from django.contrib.auth.decorators import permission_required

urlpatterns = [
                  url(r'^admin/', admin.site.urls),
                  url(r'^accounts/', include(allauth_urls)),
                  url(r'^change_status/$', permission_required('is_superuser')(views.change_status),
                      name='change_status'),
                  url(r'^$', views.index, name='index'),
                  url(r'^exchange/$', permission_required('is_superuser')(views.exchange), name='exchange'),
                  url(r'^trade/setup/(?P<pk>[0-9]+)/$', views.setup, name='tradeBotSetup'),
                  url(r'^trade/addusercoin/$', views.add_user_pair, name='add_user_pair'),
                  url(r'^trade/changerank/$', views.change_rank, name='changerank'),
                  url(r'^trade/set_share/$', views.set_share, name='set_share'),
                  url(r'^trade/set_pair_add/$', views.set_pair_add, name='set_pair_add'),
                  url(r'^trade/delete_user_pair/$', views.delete_user_pair, name='delete_user_pair'),
                  url(r'^trade/change_primary_coin/$', views.change_primary_coin, name='change_primary_coin'),
                  url(r'^trade/change_primary_coin_rank/$', views.change_primary_coin_rank,
                      name='change_primary_coin_rank'),
                  url(r'^trade/relations/$', views.relations, name='relations'),
                  url(r'^trade/exchange_script_activity/$', views.change_user_exchange_script_activity,
                      name='change_user_exchange_script_activity'),
                  url(r'^trade/exchange_trade_fake/$', views.change_user_exchange_trade_fake,
                      name='change_user_exchange_trade_fake'),
                  url(r'^trade/exchange_depth_to_trade/$', views.exchange_depth_to_trade,
                      name='exchange_depth_to_trade'),
                  url(r'^trade/get_ticker/$', views.get_ticker, name='get_ticker'),
                  url(r'^trade/get_new_orders_to_trade/$', views.get_new_to_trade, name='get_new_to_trade'),
              ] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
