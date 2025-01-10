from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.http import HttpResponseRedirect
from rangefilter.filters import DateRangeFilter  # Импорт фильтра диапазона

from django import forms

from .models import (
    Supplier,
    PriceList,
    CurrencyRate,
    Order,
    OrderItem,
    OrderProduct,
    Customer,
    DeliveryService,
    OrderStatus,
)
from .admin_site import perfume_admin_site  # Импорт кастомного сайта
from .utils.pluralize_russian import pluralize_russian as pluralize  # Импорт функции

class SupplierAdmin(admin.ModelAdmin):
    list_display = ["custom_name"]

    def custom_name(self, obj):
        return f"{obj.name}"  # Здесь создаётся кастомная строка

    custom_name.short_description = "Поставщик"  # Задаёт отображаемое имя для колонки

    def add_view(self, request, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["title"] = _("Добавить Поставщика")
        return super().add_view(request, form_url, extra_context=extra_context)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["title"] = _("Редактировать Поставщика")
        return super().change_view(
            request, object_id, form_url, extra_context=extra_context
        )

    def changelist_view(self, request, extra_context=None):
        count = Supplier.objects.count()

        title = pluralize(count, "Поставщик", "Поставщика", "Поставщиков")

        extra_context = extra_context or {}
        extra_context["title"] = title

        return super().changelist_view(request, extra_context=extra_context)


class PriceListAdmin(admin.ModelAdmin):
    list_display = ["supplier", "get_brand", "product", "price"]
    search_fields = ["product__raw_name", "product__brand__name"]
    ordering = ["product__brand__name", "supplier", "product__raw_name"]
    list_filter = ["supplier"]
    list_display_links = None

    def get_brand(self, obj):
        return obj.product.brand.name

    get_brand.short_description = "Бренд"
    get_brand.admin_order_field = "product__brand__name"

    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}

        extra_context["title"] = _("Общий прайс-лист")
        url = reverse("perfume:renew_prices")
        extra_context["custom_button"] = format_html(
            '<a class="button btn btn-primary" href="{}">Обновить прайс-листы</a>', url
        )
        return super().changelist_view(request, extra_context=extra_context)

    def has_add_permission(self, request):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        # Удаляем все действия
        actions.clear()
        return actions


class CurrencyRateAdmin(admin.ModelAdmin):
    list_display = ("currency", "rate")

    def get_model_perms(self, request):
        # Если есть одна запись - показываем модель, иначе скрываем
        if CurrencyRate.objects.count() == 0:
            CurrencyRate.objects.create(currency="USD", rate=0)
        elif CurrencyRate.objects.count() == 1:
            return super().get_model_perms(request)
        return {}

    def has_module_permission(self, request):
        # Изменяем название в списке моделей
        if CurrencyRate.objects.count() == 1:
            obj = CurrencyRate.objects.first()
            self.model._meta.verbose_name_plural = str(obj)  # "Курс USD 120,00"
        return True

    def has_add_permission(self, request):
        # Запрещаем добавление новых записей, если уже есть одна
        return not CurrencyRate.objects.exists()

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        if extra_context is None:
            extra_context = {}

        extra_context["show_save_and_continue"] = False
        extra_context["show_delete"] = False
        extra_context["show_history"] = False

        extra_context["title"] = _("Курсы валют")
        return super().changeform_view(request, object_id, form_url, extra_context)

    def changelist_view(self, request, extra_context=None):
        # Перенаправляем на редактирование, если запись одна
        if CurrencyRate.objects.count() == 1:
            obj = CurrencyRate.objects.first()
            return HttpResponseRedirect(
                reverse("admin:perfume_currencyrate_change", args=[obj.pk])
            )
        return super().changelist_view(request, extra_context)

    # Удаляем URL истории из админки
    def get_urls(self):
        urls = super().get_urls()
        urls = [url for url in urls if "history" not in url.pattern.regex.pattern]
        return urls



class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = [
        "product",
        "supplier",
        "quantity",  # Added quantity field
        "retail_price",
        "purchase_price_usd",
        "purchase_price_rub",
        "get_profit",
    ]
    readonly_fields = ["purchase_price_rub", "get_profit"]
    autocomplete_fields = ["product"]


    def get_profit(self, obj):
        if not obj.pk:
            return 0
        return (
                obj.retail_price - obj.purchase_price_rub
        ) * obj.quantity  # Updated profit calculation

    get_profit.short_description = "Прибыль (₽)"

    def get_extra(self, request, obj=None, **kwargs):
        # Если создаётся новый заказ (obj = None), возвращаем 1
        return 1 if obj is None else 0


def order_detail(obj):
    url = reverse("admin_order_detail", args=[obj.id])
    return mark_safe(f'<a href="{url}">Детали</a>')


order_detail.short_description = "Детали"


class OrderAdmin(admin.ModelAdmin):
    actions = None  # Убирает раздел "Действие"

    list_display = [
        "date",
        "get_products",
        "get_suppliers",
        "get_retail_price",
        "get_purchase_price_usd",
        "get_purchase_price_rub",
        "get_profit",
        "delivery_service",
        "status",
        "get_customer_info",
        "address",
        # order_detail,
    ]

    list_filter = [
        ("date", DateRangeFilter),
        # SpecificDateFilter,
        "status",
        "delivery_service",
        "items__supplier",
    ]

    search_fields = [
        "customer__name",
        "customer__phone",
        "items__product__name",
        "items__supplier__name",
    ]
    inlines = [OrderItemInline]

    autocomplete_fields = ["customer"]

    def get_products(self, obj):
        products = []
        for item in obj.items.all():
            url = reverse("admin:perfume_orderitem_change", args=[item.id])
            products.append(format_html('<a href="{}">{}</a>', url, item.product.name))
        return format_html("<br>".join(products))

    get_products.short_description = "Наименование товара"

    def get_suppliers(self, obj):
        suppliers = [item.supplier.name for item in obj.items.all()]
        return format_html("<br>".join(suppliers))

    get_suppliers.short_description = "Поставщик"

    def get_retail_price(self, obj):
        prices = [f"{item.retail_price * item.quantity}" for item in obj.items.all()]
        return format_html("<br>".join(prices))

    get_retail_price.short_description = "Цена ₽"

    def get_purchase_price_usd(self, obj):
        prices = [
            f"{item.purchase_price_usd * item.quantity}" for item in obj.items.all()
        ]
        return format_html("<br>".join(prices))

    get_purchase_price_usd.short_description = "Закупка USD"

    def get_purchase_price_rub(self, obj):
        prices = [
            f"{item.purchase_price_rub * item.quantity}" for item in obj.items.all()
        ]
        return format_html("<br>".join(prices))

    get_purchase_price_rub.short_description = "Закупка ₽"


    def get_profit(self, obj):
        items = obj.items.all()

        # Если в заказе один товар
        if len(items) == 1:
            item = items[0]
            return str((item.retail_price - item.purchase_price_rub) * item.quantity)

        # Если товаров больше одного
        profits = [
            str((item.retail_price - item.purchase_price_rub) * item.quantity)
            for item in items
        ]
        total_profit = sum(
            (item.retail_price - item.purchase_price_rub) * item.quantity
            for item in items
        )

        profits.append(f"<strong>Итого: {total_profit}</strong>")
        return format_html("<br>".join(profits))

    get_profit.short_description = "Прибыль ₽"

    def get_customer_info(self, obj):
        return format_html("{}, тел: {}", obj.customer.name, obj.customer.phone)

    def changelist_view(self, request, extra_context=None):
        count = Order.objects.count()

        title = pluralize(count, "Заказ", "Заказа", "Заказов")
        # Подсказка для полей поиска
        search_hint = _("Поиск доступен по полям: Имя клиента, Телефон клиента, Наименование товара, Имя поставщика.")

        extra_context = extra_context or {}
        extra_context["title"] = title
        extra_context["search_hint"] = search_hint


        return super().changelist_view(request, extra_context=extra_context)

    get_customer_info.short_description = "Контактные данные"


class OrderProductAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]

    def has_module_permission(self, request):
        return False


class CustomerAdmin(admin.ModelAdmin):
    actions = None  # Убирает раздел "Действие"

    list_display = ["name", "phone"]
    search_fields = ["name", "phone"]

    def changelist_view(self, request, extra_context=None):
        count = Customer.objects.count()

        title = pluralize(count, "Покупатель", "Покупателя", "Покупателей")

        extra_context = extra_context or {}
        extra_context["title"] = title

        return super().changelist_view(request, extra_context=extra_context)

class DeliveryServiceAdmin(admin.ModelAdmin):
    list_display = ["name", "alias", "contact_phone"]
    search_fields = ["name", "alias"]

    def has_module_permission(self, request):
        return False


class OrderStatusAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "order"]
    ordering = ["order"]

    def has_module_permission(self, request):
        return False


class OrderItemAdminForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Если объект уже существует, то отключаем редактирование поля "order"
        if self.instance and self.instance.pk:
            self.fields["order"].widget.attrs["readonly"] = True
            self.fields["order"].disabled = True

class OrderItemAdmin(admin.ModelAdmin):
    form = OrderItemAdminForm  # Если есть кастомная форма
    list_display = ["product", "supplier", "quantity", "retail_price"]

    def response_add(self, request, obj, post_url_continue=None):
        """
        Перенаправление после добавления нового объекта OrderItem.
        """
        # Всегда перенаправляем на список заказов
        return HttpResponseRedirect(reverse("admin:perfume_order_changelist"))

    def response_change(self, request, obj):
        """
        Перенаправление после сохранения изменения объекта OrderItem.
        """
        # Всегда перенаправляем на список заказов
        return HttpResponseRedirect(reverse("admin:perfume_order_changelist"))

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        """
        Настраиваем страницу редактирования/создания.
        """
        extra_context = extra_context or {}
        extra_context["title"] = _("Редактировать товар в заказе")
        extra_context["show_save_and_add_another"] = False
        extra_context["show_delete"] = True
        extra_context["show_history"] = False
        return super().changeform_view(request, object_id, form_url, extra_context=extra_context)

    def has_module_permission(self, request):
        return False



# Регистрация моделей в кастомной админке
perfume_admin_site.register(Supplier, SupplierAdmin)
perfume_admin_site.register(PriceList, PriceListAdmin)
perfume_admin_site.register(CurrencyRate, CurrencyRateAdmin)
perfume_admin_site.register(Order, OrderAdmin)
perfume_admin_site.register(OrderProduct, OrderProductAdmin)
perfume_admin_site.register(Customer, CustomerAdmin)
perfume_admin_site.register(DeliveryService, DeliveryServiceAdmin)
perfume_admin_site.register(OrderStatus, OrderStatusAdmin)
perfume_admin_site.register(OrderItem, OrderItemAdmin)
