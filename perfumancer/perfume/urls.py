from django.urls import path
from .admin_site import perfume_admin_site
from . import views

urlpatterns = [
    path('', perfume_admin_site.urls),  # Кастомный админ-сайт
    path('renew-prices/', views.renew_prices, name='renew_prices'),
]