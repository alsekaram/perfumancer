from django.db import models, transaction
from django.utils.translation import gettext_lazy as _, ngettext_lazy
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError

from decimal import Decimal

from .price_list import Supplier, CurrencyRate
from ..validators import phone_validator, email_validator


class DeliveryService(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("Название службы доставки"))
    alias = models.CharField(
        max_length=50, verbose_name=_("Псевдоним службы доставки"), unique=True
    )
    email = models.EmailField(
        verbose_name=_("Email службы доставки"),
        blank=True,
        null=True,
        validators=[email_validator],
    )
    contact_phone = models.CharField(
        max_length=20,
        verbose_name=_("Контактный телефон службы доставки"),
        blank=True,
        null=True,
        validators=[phone_validator],
    )

    class Meta:
        verbose_name = _("Служба доставки")
        verbose_name_plural = _("Службы доставки")

    def __str__(self):
        return self.name


class OrderProduct(models.Model):
    name = models.CharField(
        max_length=255, verbose_name=_("Название товара"), unique=True
    )

    class Meta:
        verbose_name = _("Товар")
        verbose_name_plural = _("Товары")

    def __str__(self):
        return self.name


class Customer(models.Model):
    name = models.CharField(max_length=255, verbose_name=_("Имя заказчика"))
    phone = models.CharField(
        max_length=20, verbose_name=_("Телефон"), validators=[phone_validator]
    )

    class Meta:
        verbose_name = _("Покупатель")
        verbose_name_plural = _("Покупатели")

    def __str__(self):
        return self.name


class OrderStatus(models.Model):
    name = models.CharField(
        max_length=50, unique=True, verbose_name=_("Название статуса")
    )
    code = models.CharField(max_length=20, unique=True, verbose_name=_("Код статуса"))
    order = models.IntegerField(verbose_name=_("Порядок отображения"))

    class Meta:
        verbose_name = _("Статус заказа")
        verbose_name_plural = _("Статусы заказов")
        ordering = ["order"]

    def __str__(self):
        return self.name


class Order(models.Model):
    # Existing fields remain the same
    date = models.DateField(verbose_name=_("Дата заказа"), default=timezone.now)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="orders",
        verbose_name=_("Заказчик"),
    )
    delivery_service = models.ForeignKey(
        DeliveryService,
        on_delete=models.CASCADE,
        related_name="orders",
        verbose_name=_("Служба доставки"),
    )
    status = models.ForeignKey(
        OrderStatus,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name=_("Статус заказа"),
    )
    address = models.TextField(verbose_name=_("Адрес доставки"))

    currency_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Курс доллара на момент создания"),
        editable=False,
        default=1.0,  # Default needed for South
    )

    def save(self, *args, **kwargs):
        if not self.pk:  # Only on creation
            rate = CurrencyRate.objects.first()
            if not rate:
                raise ValidationError(_("Не установлен курс валюты"))
            self.currency_rate = rate.rate
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Заказ")
        verbose_name_plural = _("Заказы")
        indexes = [models.Index(fields=["date", "status"])]

    def get_items_summary(self):
        """Возвращает краткую сводку по товарам в заказе"""
        items = self._get_cached_items()
        if not items:
            return "Пустой заказ"

        summary = []
        for item in items:
            summary.append(
                f"{item.product.name} x{item.quantity} " f"({item.retail_price} ₽/шт.)"
            )
        return ", ".join(summary)

    def _get_cached_items(self):
        """Helper method to cache and return order items"""
        if not hasattr(self, "_cached_items"):
            self._cached_items = list(self.items.all().select_related("product"))
        return self._cached_items

    def __str__(self):
        return (
            f"Заказ #{self.id}\n"
            f"Статус: {self.status.name}\n"
            f"Клиент: {self.customer.name}\n"
            f"Товары: {self.get_items_summary()}\n"
            f"Итого: {self.total_retail_price} ₽"
        )

    @property
    def total_retail_price(self):
        items = self._get_cached_items()
        if not items:
            return Decimal("0.00")
        return sum(item.retail_price * item.quantity for item in items)

    @property
    def total_purchase_price(self):
        items = self._get_cached_items()
        if not items:
            return Decimal("0.00")
        return sum(item.purchase_price_rub * item.quantity for item in items)

    @property
    def total_margin(self):
        items = self._get_cached_items()
        if not items:
            return Decimal("0.00")
        return self.total_retail_price - self.total_purchase_price


class OrderItem(models.Model):
    order = models.ForeignKey(
        "Order", on_delete=models.CASCADE, related_name="items", verbose_name=_("Заказ")
    )
    product = models.ForeignKey(
        "OrderProduct",
        on_delete=models.CASCADE,
        related_name="order_items",
        verbose_name=_("Товар"),
    )
    supplier = models.ForeignKey(
        "Supplier",
        on_delete=models.CASCADE,
        related_name="order_items",
        verbose_name=_("Поставщик"),
    )
    quantity = models.PositiveIntegerField(
        verbose_name=_("Количество"),
        validators=[MinValueValidator(1)],
        default=1,
    )
    retail_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Розничная цена (рубли)"),
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    purchase_price_usd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Цена закупки (в валюте)"),
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    purchase_price_rub = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Цена закупки (в рублях)"),
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    def clean(self):
        super().clean()
        if not self.order:
            raise ValidationError(_("Заказ обязателен"))

        # Use order's currency rate instead of current
        self.purchase_price_usd = self.purchase_price_usd or Decimal("0.00")
        calculated_price_rub = self.purchase_price_usd * self.order.currency_rate
        calculated_price_rub = Decimal(str(calculated_price_rub)).quantize(
            Decimal("0.01")
        )

        if self.purchase_price_rub != calculated_price_rub:
            self.purchase_price_rub = calculated_price_rub

    def save(self, *args, **kwargs):
        with transaction.atomic():
            self.clean()
            super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Товар в заказе")
        verbose_name_plural = _("Товары в заказе")

    def __str__(self):
        return f"{self.product.name} x {self.quantity} в заказе #{self.order.id}"
