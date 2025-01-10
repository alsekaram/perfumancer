from django.db import models
from django.utils.translation import gettext_lazy as _, ngettext_lazy


class Supplier(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название поставщика")
    contact_person = models.CharField(
        max_length=255, verbose_name="Контактное лицо", blank=True, null=True
    )
    phone = models.CharField(
        max_length=20, verbose_name="Телефон", blank=True, null=True
    )
    email = models.EmailField(verbose_name="Email", blank=False, null=False)
    address = models.TextField(verbose_name="Адрес", blank=True, null=True)
    website = models.URLField(verbose_name="Веб-сайт", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = _("Поставщика")
        verbose_name_plural = _("Поставщики")

    def __str__(self):
        return self.name

    @staticmethod
    def get_count_display(count):
        return ngettext_lazy("%(count)d Поставщик", "%(count)d Поставщиков", count) % {
            "count": count
        }


class ProductBase(models.Model):
    raw_name = models.CharField(max_length=250, unique=False)
    brand = models.ForeignKey(
        "Brand", on_delete=models.CASCADE, related_name="raw_products"
    )

    class Meta:
        ordering = ["raw_name"]

    def __str__(self):
        return f"{self.raw_name}"


class Product(models.Model):
    name = models.CharField(max_length=250, unique=True)
    brand = models.ForeignKey(
        "Brand", on_delete=models.CASCADE, related_name="products"
    )
    is_tester = models.BooleanField(default=False)
    volume = models.DecimalField(max_digits=5, decimal_places=1)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} (tester)" if self.is_tester else self.name


class Brand(models.Model):
    name = models.CharField(max_length=250)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Бренд"
        verbose_name_plural = "Бренды"

    def __str__(self):
        return self.name


class BrandAlias(models.Model):
    name = models.CharField(max_length=250)
    brand = models.ForeignKey("Brand", on_delete=models.CASCADE, related_name="aliases")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("name", "brand")

    def __str__(self):
        return self.name


class PriceList(models.Model):
    product = models.ForeignKey(
        ProductBase,
        on_delete=models.CASCADE,
        related_name="price_lists",
        verbose_name="Товар",
        help_text="Товар, к которому относится запись",
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name="price_lists",
        verbose_name="Поставщик",
        help_text="Поставщик, поставляющий товар",
    )
    price = models.DecimalField(
        max_digits=8, decimal_places=2, verbose_name="Цена", help_text="Цена товара"
    )

    class Meta:
        unique_together = ("product", "supplier")
        ordering = ["product"]
        verbose_name = "Прайс-лист"
        verbose_name_plural = "Прайс-листы"

    def __str__(self):
        return f"{self.product.raw_name}"

    def get_brand(self):
        return self.product.brand.name

    get_brand.short_description = "Бренд"


# простая модель для хранения курса валюты
class CurrencyRate(models.Model):
    currency = models.CharField(max_length=3, unique=True, verbose_name="Валюта")
    rate = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Курс")

    class Meta:
        verbose_name = "Курсы валют"
        verbose_name_plural = "Курс USD"

    def __str__(self):
        return f"Курс {self.currency}: {self.rate} RUB"  # Курс USD 120,00
