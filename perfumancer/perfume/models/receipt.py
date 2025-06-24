from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, FileExtensionValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
import os


class ReceiptStatus(models.Model):
    """Статусы для документов прихода"""

    DRAFT = "draft"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

    name = models.CharField(
        max_length=50, unique=True, verbose_name=_("Название статуса")
    )
    code = models.CharField(max_length=20, unique=True, verbose_name=_("Код статуса"))
    order = models.IntegerField(verbose_name=_("Порядок отображения"))

    class Meta:
        verbose_name = _("Статус прихода")
        verbose_name_plural = _("Статусы приходов")
        ordering = ["order"]

    def __str__(self):
        return self.name


class Receipt(models.Model):
    """Документ прихода товара"""

    # date = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))
    date = models.DateTimeField(
        default=timezone.now,  # Вместо auto_now_add=True
        verbose_name=_("Дата создания"),
    )
    order = models.ForeignKey(
        "Order",
        on_delete=models.PROTECT,
        related_name="receipts",
        verbose_name=_("Связанный заказ"),
        null=True,
        blank=True,
    )
    supplier = models.ForeignKey(
        "Supplier",
        on_delete=models.PROTECT,
        related_name="receipts",
        verbose_name=_("Поставщик"),
    )
    cabinet = models.ForeignKey(
        "Cabinet",
        on_delete=models.PROTECT,
        related_name="receipts",
        verbose_name=_("Кабинет/Магазин"),
    )
    invoice_number = models.CharField(
        max_length=100, blank=True, verbose_name=_("Номер накладной")
    )
    invoice_date = models.DateField(
        null=True, blank=True, verbose_name=_("Дата накладной")
    )
    status = models.ForeignKey(
        ReceiptStatus,
        on_delete=models.PROTECT,
        related_name="receipts",
        verbose_name=_("Статус"),
    )
    
    # Новое поле для хранения файла накладной
    invoice_file = models.FileField(
        upload_to='receipts/invoices/%Y/%m/',
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff']
            )
        ],
        null=True,
        blank=True,
        verbose_name=_("Файл накладной"),
        help_text=_("Загрузите скан или фото накладной (PDF, JPG, PNG и др.)")
    )

    class Meta:
        verbose_name = _("Приход")
        verbose_name_plural = _("Приходы")
        ordering = ["-date"]

    def __str__(self):
        if self.order:
            return f"Приход №{self.id} от {self.date.strftime('%d.%m.%Y')} (Заказ #{self.order.id})"
        else:
            return f"Приход №{self.id} от {self.date.strftime('%d.%m.%Y')} (Ручной)"
    
    @property
    def invoice_filename(self):
        """Возвращает только имя файла без пути"""
        if self.invoice_file:
            return os.path.basename(self.invoice_file.name)
        return None


class ReceiptItem(models.Model):
    """Позиция в документе прихода"""

    receipt = models.ForeignKey(
        Receipt,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("Приход"),
    )
    order_item = models.ForeignKey(
        "OrderItem",
        on_delete=models.PROTECT,
        related_name="receipt_items",
        verbose_name=_("Позиция заказа"),
        null=True,
        blank=True,
    )
    product_name = models.CharField(
        max_length=255, verbose_name=_("Наименование товара")
    )
    quantity_ordered = models.IntegerField(
        verbose_name=_("Заказано"),
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    quantity_received = models.IntegerField(
        default=0,
        verbose_name=_("Фактически получено"),
        validators=[MinValueValidator(0)],
    )
    purchase_price_usd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Фактическая цена закупки (USD)"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    purchase_price_rub = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Фактическая цена закупки (RUB)"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        verbose_name = _("Позиция прихода")
        verbose_name_plural = _("Позиции прихода")
        # unique_together = ("receipt", "order_item")

    def __str__(self):
        return f"{self.product_name} - {self.quantity_received} шт."

    def clean(self):
        """Валидация позиции прихода"""
        super().clean()

        if self.purchase_price_usd < 0:
            raise ValidationError(
                {"purchase_price_usd": _("Цена не может быть отрицательной.")}
            )

        if self.purchase_price_rub < 0:
            raise ValidationError(
                {"purchase_price_rub": _("Цена не может быть отрицательной.")}
            )
