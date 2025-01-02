from django.urls import path
from .admin_site import perfume_admin_site
from . import views

urlpatterns = [
    path('task_status/<str:task_id>/', views.task_status, name='task_status'),
    path('', perfume_admin_site.urls),  # Кастомный админ-сайт
    path('renew-prices/', views.renew_prices, name='renew_prices'),
    path('download-prices/', views.download_prices, name='download_prices'),
]
