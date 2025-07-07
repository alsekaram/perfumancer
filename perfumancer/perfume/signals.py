from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.db import transaction
from .models import Order, Receipt, ReceiptItem, ReceiptStatus
from .utils.file_processor import process_invoice_file


@receiver(pre_save, sender=Order)
def cache_old_status(sender, instance, **kwargs):
    """Кэширует старый статус заказа перед сохранением"""
    if instance.pk:
        try:
            old_instance = Order.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except Order.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Order)
def create_receipts_on_order_status_change(sender, instance, created, **kwargs):
    """Создает документы прихода при изменении статуса заказа на 'Заказан'"""

    # Проверяем, что статус действительно изменился на "Заказан"
    old_status = getattr(instance, "_old_status", None)

    # Если статус не изменился или новый статус не 'ordered', выходим
    if old_status == instance.status or instance.status.code != "ordered":
        return

    # Проверяем, что заказ не пустой
    if not instance.items.exists():
        return

    with transaction.atomic():
        # Получаем кабинет из первой позиции заказа
        # TODO: В будущем перенести cabinet на уровень Order
        first_item = instance.items.first()
        if not first_item or not first_item.cabinet_id:
            print(f"Предупреждение: Заказ #{instance.id} не имеет позиций с кабинетом")
            return

        order_cabinet_id = first_item.cabinet_id

        # Проверяем, что все позиции из одного кабинета (валидация)
        different_cabinets = (
            instance.items.exclude(cabinet_id=order_cabinet_id)
            .values_list("cabinet_id", flat=True)
            .distinct()
        )

        if different_cabinets:
            print(f"ВНИМАНИЕ: В заказе #{instance.id} позиции из разных кабинетов!")
            # Можно выбросить исключение или продолжить с предупреждением

        # Группируем позиции заказа только по поставщикам
        items_by_supplier = {}
        for item in instance.items.all():
            if item.supplier_id not in items_by_supplier:
                items_by_supplier[item.supplier_id] = []
            items_by_supplier[item.supplier_id].append(item)

        # ИСПРАВЛЕНИЕ: Получаем существующие приходы для этого заказа по поставщикам
        existing_receipts = set(instance.receipts.values_list("supplier_id", flat=True))

        # Получаем или создаем статус "Черновик"
        draft_status, _ = ReceiptStatus.objects.get_or_create(
            code="draft", defaults={"name": "Черновик", "order": 1}
        )

        # ИСПРАВЛЕНИЕ: Создаем приход только для поставщиков, у которых еще нет прихода
        for supplier_id, items in items_by_supplier.items():
            # Проверяем, есть ли уже приход для этого конкретного поставщика
            if supplier_id in existing_receipts:
                print(f"Приход для поставщика {supplier_id} уже существует, пропускаем")
                continue

            receipt = Receipt.objects.create(
                order=instance,
                supplier_id=supplier_id,
                cabinet_id=order_cabinet_id,  # Используем общий кабинет заказа
                status=draft_status,
            )

            # Создаем позиции прихода
            for item in items:
                ReceiptItem.objects.create(
                    receipt=receipt,
                    order_item=item,
                    product_name=item.product.name,
                    quantity_ordered=item.quantity,
                    quantity_received=0,
                    purchase_price_usd=item.purchase_price_usd,
                    purchase_price_rub=item.purchase_price_rub,
                )

            print(f"Создан приход №{receipt.id} для поставщика {receipt.supplier}")


@receiver(pre_save, sender=Receipt)
def process_receipt_invoice_file(sender, instance, **kwargs):
    """
    Обрабатывает файл накладной перед сохранением:
    - Конвертирует HEIC в JPEG
    """
    if instance.invoice_file and hasattr(instance.invoice_file, 'file'):
        # Проверяем, что файл был изменен
        try:
            # Если это новый объект или файл был изменен
            if not instance.pk:
                # Новый объект - обрабатываем файл
                instance.invoice_file = process_invoice_file(instance.invoice_file)
            else:
                # Существующий объект - проверяем, изменился ли файл
                original = Receipt.objects.get(pk=instance.pk)
                if original.invoice_file != instance.invoice_file:
                    instance.invoice_file = process_invoice_file(instance.invoice_file)
        except Receipt.DoesNotExist:
            # Объект еще не существует в БД, обрабатываем файл
            instance.invoice_file = process_invoice_file(instance.invoice_file)
        except Exception as e:
            # Логируем ошибку, но не прерываем сохранение
            print(f"Ошибка обработки файла накладной: {e}")
