from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.http import HttpResponseRedirect
from rangefilter.filters import DateRangeFilter  # Импорт фильтра диапазона
from django.db.models import Sum, F, ExpressionWrapper, DecimalField, Count, Max
from django.template.response import TemplateResponse
from django.forms.widgets import Select
from django.db.models import F, Sum, DecimalField, ExpressionWrapper

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
    Receipt,
    ReceiptItem,
    ReceiptStatus,
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
                reverse("perfume:perfume_currencyrate_change", args=[obj.pk])
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
        "get_receipt_links",
    ]
    readonly_fields = ["purchase_price_rub", "get_profit", "get_receipt_links"]
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

    def get_receipt_links(self, obj):
        if not obj.pk:
            return "-"

        receipt_links = []
        for receipt_item in obj.receipt_items.select_related(
            "receipt", "receipt__status"
        ).all():
            receipt = receipt_item.receipt
            url = reverse("perfume:perfume_receipt_change", args=[receipt.id])
            status_color = {
                "draft": "#ffc107",  # желтый
                "completed": "#28a745",  # зеленый
                "cancelled": "#dc3545",  # красный
            }.get(receipt.status.code, "#6c757d")

            receipt_links.append(
                format_html(
                    '<a href="{}" style="color: {}; font-weight: bold;">Приход №{}</a> ({})',
                    url,
                    status_color,
                    receipt.id,
                    receipt.status.name,
                )
            )
        return format_html("<br>".join(receipt_links)) if receipt_links else "-"

    get_receipt_links.short_description = "Приходы"


def order_detail(obj):
    url = reverse("perfume:admin_order_detail", args=[obj.id])
    return mark_safe(f'<a href="{url}">Детали</a>')


order_detail.short_description = "Детали"


class OrderAdmin(admin.ModelAdmin):
    actions = None

    list_display = [
        "date",
        "get_products",
        "get_suppliers",
        "get_cabinets",
        "get_receipts_info",
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
            url = reverse("perfume:perfume_orderitem_change", args=[item.id])
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
            reverse("perfume:perfume_order_changelist")
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

        if "customer__id__exact" in request.GET:
            try:
                customer_id = request.GET["customer__id__exact"]
                customer = Customer.objects.get(id=customer_id)

                from django.contrib import messages

                messages.info(
                    request,
                    format_html(
                        "Показаны заказы покупателя: <strong>{}</strong>. "
                        '<a href="{}">Сбросить фильтр</a>',
                        customer.name,
                        reverse("perfume:perfume_order_changelist"),
                    ),
                )
            except (Customer.DoesNotExist, ValueError):
                pass

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

    def has_delete_permission(self, request, obj=None):
        if obj:
            # Проверяем наличие проведенных приходов
            completed_receipts = obj.receipts.exclude(status__code="draft")
            if completed_receipts.exists():
                return False
        return super().has_delete_permission(request, obj)

    def delete_model(self, request, obj):
        """Кастомное удаление с предварительной очисткой черновиков"""
        # Удаляем черновики приходов
        draft_receipts = obj.receipts.filter(status__code="draft")
        draft_receipts.delete()

        # Удаляем заказ
        super().delete_model(request, obj)

        from django.contrib import messages

        messages.success(
            request, f"Заказ #{obj.id} и связанные черновики приходов удалены"
        )

    def delete_queryset(self, request, queryset):
        """Массовое удаление заказов"""
        deleted_count = 0
        errors = []

        for order in queryset:
            try:
                # Удаляем черновики
                draft_receipts = order.receipts.filter(status__code="draft")
                draft_receipts.delete()

                # Проверяем наличие других приходов
                remaining_receipts = order.receipts.exclude(status__code="draft")
                if remaining_receipts.exists():
                    errors.append(f"Заказ #{order.id} имеет проведенные приходы")
                    continue

                order.delete()
                deleted_count += 1

            except Exception as e:
                errors.append(f"Ошибка при удалении заказа #{order.id}: {str(e)}")

        from django.contrib import messages

        if deleted_count:
            messages.success(request, f"Удалено заказов: {deleted_count}")
        if errors:
            messages.error(request, "Ошибки: " + "; ".join(errors))

    def get_receipts_info(self, obj):
        receipts = obj.receipts.all()
        if not receipts:
            if obj.status.code == "ordered":
                return format_html(
                    '<span style="color: #ffc107;">⏳ Ожидают создания</span>'
                )
            return "-"

        receipt_links = []
        for receipt in receipts:
            url = reverse("perfume:perfume_receipt_change", args=[receipt.id])
            status_color = {
                "draft": "#ffc107",
                "completed": "#28a745",
                "cancelled": "#dc3545",
            }.get(receipt.status.code, "#6c757d")

            receipt_links.append(
                format_html(
                    '<a href="{}" style="color: {};">№{}</a>',
                    url,
                    status_color,
                    receipt.id,
                )
            )

        return format_html(" | ".join(receipt_links))

    get_receipts_info.short_description = "Приходы"


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
    actions = None
    list_display = [
        "name",
        "phone",
        "get_orders_info",
        "get_last_order_date",
        "get_total_spent",
    ]
    search_fields = ["name", "phone"]
    ordering = ["name"]  # Сортировка по умолчанию

    # Для autocomplete
    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(
            request, queryset, search_term
        )

        # Аннотируем количеством заказов
        queryset = queryset.annotate(orders_count=Count("orders"))

        return queryset, use_distinct

    # Переопределяем отображение в autocomplete
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Всегда аннотируем количеством заказов
        return qs.annotate(
            orders_count=Count("orders"),
            last_order_date=Max("orders__date"),
            total_spent=Sum(
                F("orders__items__retail_price") * F("orders__items__quantity")
            ),
        )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                orders_count=Count("orders"),
                last_order_date=Max("orders__date"),
                total_spent=Sum(
                    F("orders__items__retail_price") * F("orders__items__quantity")
                ),
            )
        )

    def get_orders_info(self, obj):
        count = obj.orders_count
        if count > 0:
            # URL для перехода к отфильтрованным заказам
            orders_url = (
                reverse("perfume:perfume_order_changelist")
                + f"?customer__id__exact={obj.id}"
            )

            return format_html(
                '<a href="{}">{}</a>',
                orders_url,
                pluralize(count, "заказ", "заказа", "заказов"),
            )
        return format_html('<span style="color: #999;">Нет заказов</span>')

    get_orders_info.short_description = "Заказы"
    get_orders_info.admin_order_field = "orders_count"  # Делаем колонку сортируемой

    def get_last_order_date(self, obj):
        if obj.last_order_date:
            return obj.last_order_date.strftime("%d.%m.%Y")
        return "-"

    get_last_order_date.short_description = "Последний заказ"
    get_last_order_date.admin_order_field = "last_order_date"  # Делаем сортируемой

    def get_total_spent(self, obj):
        if obj.total_spent:
            return f"{obj.total_spent:,.2f} ₽"
        return "0 ₽"

    get_total_spent.short_description = "Сумма покупок"
    get_total_spent.admin_order_field = "total_spent"  # Делаем сортируемой


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
        return HttpResponseRedirect(reverse("perfume:perfume_order_changelist"))

    def response_change(self, request, obj):
        """Handle response after changing OrderItem"""
        if "_continue" in request.POST:
            return super().response_change(request, obj)
        return HttpResponseRedirect(reverse("perfume:perfume_order_changelist"))

    def response_delete(self, request, obj_display, obj_id):
        """
        Перенаправление после удаления объекта OrderItem.
        """
        # Всегда перенаправляем на список заказов
        return HttpResponseRedirect(reverse("perfume:perfume_order_changelist"))

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


class ReceiptItemInline(admin.TabularInline):
    model = ReceiptItem
    extra = 0
    fields = [
        # "order_item",
        "product_name",
        "quantity_ordered",
        "quantity_received",
        "purchase_price_usd",
        "purchase_price_rub",
    ]

    # raw_id_fields = ["order_item"]

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status.code == "completed":
            # Только для "проведенных" все поля readonly
            return list(self.fields)
        elif obj and obj.status.code == "cancelled":
            # Для "отказанных" можно менять только статус (через родительский объект)
            return list(self.fields)
        return []  # Для черновиков все можно редактировать

    def has_add_permission(self, request, obj=None):
        # Добавление позиций только для черновиков
        if obj and obj.status.code != "draft":
            return False
        return super().has_add_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        # Удаление позиций только для черновиков
        if obj and obj.status.code != "draft":
            return False
        return super().has_delete_permission(request, obj)

    def get_extra(self, request, obj=None, **kwargs):
        # Пустые строки только для черновиков
        if obj and obj.status.code != "draft":
            return 0
        return 1 if obj is None else 0


class ReceiptAdmin(admin.ModelAdmin):
    list_display = [
        "get_receipt_number",
        "date",
        "supplier",
        "cabinet",
        "get_order_link",
        "invoice_number",
        "invoice_date",
        "get_invoice_file",
        "get_status_display",
        "get_items_count",
        "get_total_amount",
    ]

    list_filter = ["status", "supplier", "cabinet", "date"]
    search_fields = ["invoice_number", "order__id", "supplier__name"]
    inlines = [ReceiptItemInline]

    # Фиксированный порядок полей
    fields = [
        "date",
        "supplier",
        "cabinet",
        "invoice_number",
        "invoice_date",
        "invoice_file",
        "order",
        "status",
    ]

    def get_receipt_number(self, obj):
        return f"Приход №{obj.id}"

    get_receipt_number.short_description = "Номер"

    def get_order_link(self, obj):
        if obj.order:
            url = reverse("perfume:perfume_order_change", args=[obj.order.id])
            return format_html('<a href="{}">Заказ #{}</a>', url, obj.order.id)
        return "Без заказа"

    get_order_link.short_description = "Заказ"
    
    def get_invoice_file(self, obj):
        """Отображение файла накладной"""
        if obj.invoice_file:
            file_url = obj.invoice_file.url
            file_name = obj.invoice_filename
            # Определяем иконку в зависимости от расширения
            if file_name.lower().endswith('.pdf'):
                icon = '📄'
            else:
                icon = '🖼️'
            return format_html(
                '<a href="{}" target="_blank">{} {}</a>',
                file_url,
                icon,
                file_name
            )
        return "-"
    
    get_invoice_file.short_description = "Файл"

    def get_items_count(self, obj):
        return obj.items.count()

    get_items_count.short_description = "Позиций"

    def get_total_amount(self, obj):
        total = (
            obj.items.aggregate(
                total=Sum(
                    ExpressionWrapper(
                        F("quantity_received") * F("purchase_price_usd"),
                        output_field=DecimalField(),
                    )
                )
            )["total"]
            or 0
        )
        return f"${total:,.2f}"

    get_total_amount.short_description = "Сумма"

    def get_readonly_fields(self, request, obj=None):
        readonly = []

        # Если это существующий объект
        if obj:
            # Заказ можно менять только у ручных приходов в статусе черновик
            if obj.order or obj.status.code != "draft":
                readonly.append("order")
            readonly.append("date")

            # Если приход не черновик, блокируем дополнительные поля
            if obj.status.code != "draft":
                readonly.extend(
                    ["invoice_number", "invoice_date", "invoice_file", "supplier", "cabinet"]
                )

        return readonly

    def save_model(self, request, obj, form, change):
        """Переопределяем сохранение модели для обработки ручных приходов"""
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        """Сохранение позиций прихода"""
        instances = formset.save(commit=False)

        for instance in instances:
            # Для ручных приходов quantity_ordered может быть пустым
            if not instance.quantity_ordered:
                instance.quantity_ordered = instance.quantity_received
            instance.save()

        formset.save_m2m()

    def has_delete_permission(self, request, obj=None):
        if obj and obj.status.code != "draft":
            return False
        return super().has_delete_permission(request, obj)

    def get_status_display(self, obj):
        """Отображение статуса с цветом"""
        color_map = {
            "draft": "#ffc107",  # желтый
            "completed": "#28a745",  # зеленый
            "cancelled": "#dc3545",  # красный
        }
        color = color_map.get(obj.status.code, "#6c757d")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.status.name,
        )

    get_status_display.short_description = "Статус"


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
perfume_admin_site.register(Receipt, ReceiptAdmin)
