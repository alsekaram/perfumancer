from django.contrib.admin import AdminSite, SimpleListFilter
from django.urls import reverse
from django.urls import path
from . import views
from django.contrib import admin
from django.utils.translation import ngettext



from .models import Brand, Supplier, PriceList, ProductBase

class PerfumeAdminSite(AdminSite):
    site_header = "Perfumаncer"
    site_title = "Perfumancer"
    index_title = "Perfume"
    login_template = 'admin/login.html'  # Используем стандартный шаблон входа

    def each_context(self, request):
        """
        Добавляем контекст для кастомного сайта.
        """
        context = super().each_context(request)
        context['site_url'] = reverse('perfume:login')
        return context

    def has_permission(self, request):
        """
        Проверяем, есть ли у пользователя доступ к кастомному сайту.
        """
        return request.user.is_active and request.user.is_staff


    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('renew-prices/', self.admin_view(views.renew_prices), name='renew_prices'),
        ]
        return custom_urls + urls


perfume_admin_site = PerfumeAdminSite(name='perfume')


