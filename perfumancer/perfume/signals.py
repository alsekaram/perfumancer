from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.db import transaction
from .models import Order, Receipt, ReceiptItem, ReceiptStatus
from .utils.file_processor import process_invoice_file
import subprocess
from pathlib import Path
from django.conf import settings
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from .models import Receipt
import logging

logger = logging.getLogger(__name__)


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


@receiver(post_save, sender=Receipt)
def cache_invoice_file_on_save(sender, instance, created, **kwargs):
    """
    Кэширует файл накладной локально при сохранении
    """
    if instance.invoice_file:
        cache_file_from_s3(instance)

def cache_file_from_s3(receipt_instance):
    """
    Скачивает файл с S3 в локальный кэш
    """
    try:
        # Путь к локальному кэшу
        cache_dir = Path(settings.INVOICE_CACHE_ROOT) / str(receipt_instance.id)
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        filename = receipt_instance.invoice_filename
        local_file_path = cache_dir / filename
        
        # Если файл уже есть - не перекачиваем
        if local_file_path.exists():
            logger.info(f"Файл накладной {receipt_instance.id} уже в кэше: {filename}")
            return True
        
        # Получаем S3 URL
        s3_url = receipt_instance.invoice_file.url
        
        # Скачиваем через curl (не блокирует GIL)
        result = subprocess.run([
            'curl', '-s', '-L', '--max-time', '30', 
            '-o', str(local_file_path), s3_url
        ], capture_output=True, timeout=35)
        
        if result.returncode == 0 and local_file_path.exists():
            logger.info(f"Файл накладной {receipt_instance.id} скачан в кэш: {filename}")
            return True
        else:
            logger.error(f"Ошибка скачивания файла накладной {receipt_instance.id}: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка кэширования файла накладной {receipt_instance.id}: {e}")
        return False

@receiver(pre_delete, sender=Receipt)
def cleanup_cached_file_on_delete(sender, instance, **kwargs):
    """
    Удаляет локальный кэш при удалении накладной
    """
    try:
        cache_dir = Path(settings.INVOICE_CACHE_ROOT) / str(instance.id)
        if cache_dir.exists():
            import shutil
            shutil.rmtree(cache_dir)
            logger.info(f"Удален локальный кэш для накладной {instance.id}")
    except Exception as e:
        logger.error(f"Ошибка удаления кэша накладной {instance.id}: {e}")
