from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.http import HttpResponseRedirect
from rangefilter.filters import DateRangeFilter  # Импорт фильтра диапазона
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from django.template.response import TemplateResponse
from django.forms.widgets import Select

from decimal import Decimal

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
    Cabinet,
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
        if extra_context is None:
            extra_context = {}
        original_verbose_name_plural = self.model._meta.verbose_name_plural

        plural_text = pluralize(count, "Поставщик", "Поставщика", "Постащиков")

        extra_context["title"] = plural_text

        response = super().changelist_view(request, extra_context=extra_context)

        # Меняем значение для нижней части списка
        self.model._meta.verbose_name_plural = plural_text.split(" ", 1)[1]

        # Возвращаем значение после формирования ответа
        if isinstance(response, TemplateResponse):
            response.add_post_render_callback(
                lambda r: setattr(
                    self.model._meta,
                    "verbose_name_plural",
                    original_verbose_name_plural,
                )
            )

        return response


class PriceListAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("product", "product__brand", "supplier")
        )

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
        count = PriceList.objects.count()
        if extra_context is None:
            extra_context = {}

        extra_context["title"] = _("Общий прайс-лист")
        url = reverse("perfume:renew_prices")
        extra_context["custom_button"] = format_html(
            '<a class="button btn btn-primary" href="{}">Обновить прайс-листы</a>', url
        )

        original_verbose_name_plural = self.model._meta.verbose_name_plural

        plural_text = pluralize(count, "Прайс", "Прайса", "Прайсов")

        extra_context["title"] = plural_text

        response = super().changelist_view(request, extra_context=extra_context)

        # Меняем значение для нижней части списка
        self.model._meta.verbose_name_plural = plural_text.split(" ", 1)[1]

        # Возвращаем значение после формирования ответа
        if isinstance(response, TemplateResponse):
            response.add_post_render_callback(
                lambda r: setattr(
                    self.model._meta,
                    "verbose_name_plural",
                    original_verbose_name_plural,
                )
            )

        return response

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
        "cabinet",
        "quantity",
        "retail_price",
        "purchase_price_usd",
        "purchase_price_rub",
        "get_profit",
    ]
    readonly_fields = ["purchase_price_rub", "get_profit"]
    autocomplete_fields = ["product"]

    def get_profit(self, obj):
        if not obj.pk:
            return Decimal("0.00")
        # Convert quantity to Decimal before multiplication
        quantity = Decimal(str(obj.quantity))
        profit = (obj.retail_price - obj.purchase_price_rub) * quantity
        return profit.quantize(Decimal("0.01"))

    get_profit.short_description = "Прибыль (₽)"

    def get_extra(self, request, obj=None, **kwargs):
        return 1 if obj is None else 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Переопределяем метод для фильтрации queryset для полей ForeignKey
        if db_field.name == "cabinet":
            kwargs["queryset"] = Cabinet.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == "quantity":
            # Ensure quantity is treated as Decimal
            formfield.widget.attrs["step"] = "1"
            formfield.widget.attrs["min"] = "1"
        # Изменяем виджет для поля cabinet
        if db_field.name == "cabinet":
            # Используем простой Select виджет без редактирования
            formfield.widget = Select(choices=formfield.widget.choices)
        return formfield


def order_detail(obj):
    url = reverse("admin_order_detail", args=[obj.id])
    return mark_safe(f'<a href="{url}">Детали</a>')


order_detail.short_description = "Детали"


class OrderAdmin(admin.ModelAdmin):
    actions = None

    list_display = [
        "date",
        "get_products",
        "get_suppliers",
        "get_cabinets",
        # "get_retail_price", # Можно даже заменить на столбец с Розничная цена (рубли)(в целом он не нужен там
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
        "status",
        "delivery_service",
        "items__supplier",
        "items__cabinet",
    ]

    search_fields = [
        "customer__name",
        "customer__phone",
        "items__product__name",
        "items__supplier__name",
    ]
    inlines = [OrderItemInline]

    autocomplete_fields = ["customer"]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                "items__product",
                "items__supplier",
                "customer",
            )
            .annotate(
                total_retail=Sum(F("items__retail_price") * F("items__quantity")),
                total_purchase_usd=Sum(
                    F("items__purchase_price_usd") * F("items__quantity")
                ),
                total_purchase_rub=Sum(
                    F("items__purchase_price_rub") * F("items__quantity")
                ),
                total_profit=Sum(
                    (F("items__retail_price") - F("items__purchase_price_rub"))
                    * F("items__quantity")
                ),
            )
            .order_by("-date")
        )

    def get_products(self, obj):
        if not obj.items.exists():
            return "-"
        products = []
        for item in obj.items.all():
            url = reverse("admin:perfume_orderitem_change", args=[item.id])
            products.append(
                format_html(
                    '<a href="{}">{} ({}шт)</a>', url, item.product.name, item.quantity
                )
            )
        return format_html("<br>".join(products))

    get_products.short_description = "Наименование товара"

    def get_cabinets(self, obj):
        """Отображает кабинеты для товаров в заказе"""
        if not obj.items.exists():
            return "-"
        cabinets = []
        for item in obj.items.all():
            if item.cabinet:
                cabinets.append(f"{item.cabinet.name}")
            else:
                cabinets.append("-")
        return format_html("<br>".join(cabinets))

    get_cabinets.short_description = "Магазин"

    def get_suppliers(self, obj):
        if not obj.items.exists():
            return "-"
        suppliers = [f"{item.supplier.name}" for item in obj.items.all()]
        return format_html("<br>".join(suppliers))

    get_suppliers.short_description = "Поставщик"

    def get_retail_price(self, obj):
        if not obj.items.exists():
            return "-"
        prices = []
        for item in obj.items.all():
            price = (item.retail_price * item.quantity).quantize(Decimal("0.01"))
            prices.append(f"{price:,.2f} ₽")
        if len(prices) > 1:
            total = obj.total_retail.quantize(Decimal("0.01"))
            prices.append(f"<strong>Итого: {total:,.2f} ₽</strong>")
        return format_html("<br>".join(prices))

    get_retail_price.short_description = "Цена ₽"

    def get_purchase_price_usd(self, obj):
        if not obj.items.exists():
            return "-"
        prices = []
        for item in obj.items.all():
            price = (item.purchase_price_usd * item.quantity).quantize(Decimal("0.01"))
            prices.append(f"${price:,.2f}")
        if len(prices) > 1:
            total = obj.total_purchase_usd.quantize(Decimal("0.01"))
            prices.append(f"<strong>Итого: ${total:,.2f}</strong>")
        return format_html("<br>".join(prices))

    get_purchase_price_usd.short_description = "Закупка USD"

    def get_purchase_price_rub(self, obj):
        if not obj.items.exists():
            return "-"
        prices = []
        for item in obj.items.all():
            price = (item.purchase_price_rub * item.quantity).quantize(Decimal("0.01"))
            prices.append(f"{price:,.2f} ₽")
        if len(prices) > 1:
            total = obj.total_purchase_rub.quantize(Decimal("0.01"))
            prices.append(f"<strong>Итого: {total:,.2f} ₽</strong>")
        return format_html("<br>".join(prices))

    get_purchase_price_rub.short_description = "Закупка ₽"

    def get_profit(self, obj):
        if not obj.items.exists():
            return "-"
        profits = []
        for item in obj.items.all():
            profit = (
                (item.retail_price - item.purchase_price_rub) * item.quantity
            ).quantize(Decimal("0.01"))
            profits.append(f"{profit:,.2f} ₽")
        if len(profits) > 1:
            total = obj.total_profit.quantize(Decimal("0.01"))
            profits.append(f"<strong>Итого: {total:,.2f} ₽</strong>")
        return format_html("<br>".join(profits))

    get_profit.short_description = "Прибыль ₽"

    def get_customer_info(self, obj):
        if not obj.customer:
            return "-"

        # URL для фильтрации заказов по покупателю
        url = (
            reverse("admin:perfume_order_changelist")
            + f"?customer__id__exact={obj.customer.id}"
        )

        # Кликабельное имя покупателя
        customer_link = format_html(
            '<a href="{}" title="Показать все заказы покупателя">{}</a>',
            url,
            obj.customer.name,
        )

        return format_html("{}, тел: {}", customer_link, obj.customer.phone or "-")

    get_customer_info.short_description = "Контактные данные"
    get_customer_info.allow_tags = True

    def changelist_view(self, request, extra_context=None):
        count = Order.objects.count()
        extra_context = extra_context or {}
        original_verbose_name_plural = self.model._meta.verbose_name_plural

        plural_text = pluralize(count, "Заказ", "Заказа", "Заказов")

        extra_context["title"] = plural_text

        response = super().changelist_view(request, extra_context=extra_context)

        # Меняем значение для нижней части списка
        self.model._meta.verbose_name_plural = plural_text.split(" ", 1)[1]

        # Возвращаем значение после формирования ответа
        if isinstance(response, TemplateResponse):
            response.add_post_render_callback(
                lambda r: setattr(
                    self.model._meta,
                    "verbose_name_plural",
                    original_verbose_name_plural,
                )
            )

        return response

    get_customer_info.short_description = "Контактные данные"


class OrderProductAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]

    def has_module_permission(self, request):
        return False


class CabinetAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "is_active"]
    search_fields = ["name", "code"]
    list_filter = ["is_active"]

    def changelist_view(self, request, extra_context=None):
        count = self.model.objects.count()
        extra_context = extra_context or {}
        original_verbose_name_plural = self.model._meta.verbose_name_plural

        plural_text = pluralize(count, "Кабинет", "Кабинета", "Кабинетов")

        extra_context["title"] = plural_text

        response = super().changelist_view(request, extra_context=extra_context)

        # Меняем значение для нижней части списка
        self.model._meta.verbose_name_plural = plural_text.split(" ", 1)[1]

        # Возвращаем значение после формирования ответа
        if isinstance(response, TemplateResponse):
            response.add_post_render_callback(
                lambda r: setattr(
                    self.model._meta,
                    "verbose_name_plural",
                    original_verbose_name_plural,
                )
            )

        return response


class CustomerAdmin(admin.ModelAdmin):
    actions = None  # Убирает раздел "Действие"

    list_display = ["name", "phone"]
    search_fields = ["name", "phone"]

    def changelist_view(self, request, extra_context=None):
        count = self.model.objects.count()
        original_verbose_name_plural = self.model._meta.verbose_name_plural

        plural_text = pluralize(count, "Покупатель", "Покупателя", "Покупателей")

        extra_context = extra_context or {}
        extra_context["title"] = plural_text

        response = super().changelist_view(request, extra_context=extra_context)

        # Меняем значение для нижней части списка
        self.model._meta.verbose_name_plural = plural_text.split(" ", 1)[1]

        # Возвращаем значение после формирования ответа
        if isinstance(response, TemplateResponse):
            response.add_post_render_callback(
                lambda r: setattr(
                    self.model._meta,
                    "verbose_name_plural",
                    original_verbose_name_plural,
                )
            )

        return response


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
    form = OrderItemAdminForm
    list_display = ["product", "supplier", "cabinet", "quantity", "retail_price"]

    def response_add(self, request, obj, post_url_continue=None):
        """Handle response after adding new OrderItem"""
        if "_continue" in request.POST:
            return super().response_add(request, obj, post_url_continue)
        return HttpResponseRedirect(reverse("admin:perfume_order_changelist"))

    def response_change(self, request, obj):
        """Handle response after changing OrderItem"""
        if "_continue" in request.POST:
            return super().response_change(request, obj)
        return HttpResponseRedirect(reverse("admin:perfume_order_changelist"))

    def response_delete(self, request, obj_display, obj_id):
        """
        Перенаправление после удаления объекта OrderItem.
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
        return super().changeform_view(
            request, object_id, form_url, extra_context=extra_context
        )

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
perfume_admin_site.register(Cabinet, CabinetAdmin)
