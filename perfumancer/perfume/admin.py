from django.utils.translation import ngettext, gettext_lazy as _
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.http import HttpResponse

from .models import Supplier, PriceList
from .admin_site import perfume_admin_site  # Импорт кастомного сайта

class SupplierAdmin(admin.ModelAdmin):
    list_display = ['custom_name']

    def custom_name(self, obj):
        return f"{obj.name}"  # Здесь создаётся кастомная строка

    custom_name.short_description = "Поставщик"  # Задаёт отображаемое имя для колонки

    def add_view(self, request, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['title'] = _("Добавить Поставщика")
        return super().add_view(request, form_url, extra_context=extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['title'] = _("Редактировать Поставщика")
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def changelist_view(self, request, extra_context=None):
        count = Supplier.objects.count()
        extra_context = extra_context or {}
        extra_context['title'] = ngettext(
            "%d Поставщик", "%d Поставщиков", count
        ) % count
        # extra_context['cl'] = {
        #     'result_count': count,  # Связываем с ключом общего отображения
        # }
        print(extra_context)
        return super().changelist_view(request, extra_context=extra_context)



class PriceListAdmin(admin.ModelAdmin):
    list_display = ['supplier', 'get_brand', 'product', 'price']
    search_fields = ['product__raw_name', 'product__brand__name']
    ordering = ['product__brand__name', 'supplier', 'product__raw_name']
    list_filter = ['supplier']  # Ваш кастомный фильтр
    list_display_links = None  # Отключает ссылки для всех колонок

    def get_brand(self, obj):
        return obj.product.brand.name
    get_brand.short_description = "Бренд"
    get_brand.admin_order_field = 'product__brand__name'

    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}

        extra_context['title'] = _("Общий прайс-лист")  # Или оставьте пустым: ""
        # Используем правильное namespace
        url = reverse('perfume:renew_prices')  # Здесь 'perfume' — namespace кастомного админ-сайта
        extra_context['custom_button'] = format_html(
            '<a class="button btn btn-primary" href="{}">Обновить прайс-листы</a>',
            url
        )
        return super().changelist_view(request, extra_context=extra_context)

    def has_add_permission(self, request):
        # Запрещаем отображение кнопки "Добавить" на странице "Прайс-листы"
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        # Удаляем все действия
        actions.clear()
        return actions


# Регистрация моделей в кастомной админке
perfume_admin_site.register(Supplier, SupplierAdmin)  # Зарегистрируем Supplier
perfume_admin_site.register(PriceList, PriceListAdmin)  # Зарегистрируем PriceList
