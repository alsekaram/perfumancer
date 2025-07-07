from django.core.cache import cache
from django.http import JsonResponse, HttpResponse, Http404
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseForbidden
from django.http import HttpResponseRedirect
from django.utils.http import quote

from .tasks import update_prices_task
from .models import Order, Receipt

from celery.result import AsyncResult
from pathlib import Path
import os
import logging
import requests
from pathlib import Path
from django.conf import settings
from django.http import HttpResponseRedirect
import subprocess

logger = logging.getLogger(__name__)

# Определяем базовый путь (каталог, где находится manage.py)
BASE_DIR = Path(
    __file__).resolve().parent.parent.parent  # возможно, нужно больше .parent в зависимости от структуры


def renew_prices(request):
    if request.method == "POST":
        # Проверяем блокировку в кэше
        if cache.get("renew_prices_task_lock"):
            return JsonResponse({"error": "Задача уже выполняется"}, status=400)

        # Устанавливаем блокировку
        cache.set("renew_prices_task_lock", True, timeout=160)  # 1 час

        # Запускаем задачу
        task = update_prices_task.delay()
        logger.info(f"Запущена задача обновления цен: {task.id}")
        return JsonResponse({"task_id": task.id})

    return redirect("/perfume/pricelist/")


def task_status(request, task_id):
    result = AsyncResult(task_id)
    logger.info(f"Статус задачи {task_id}: {result.state}")
    if result.state in ["PENDING", "FAILURE"]:
        return JsonResponse({"status": "NOT FOUND"}, status=404)
    # удаляем из кеша блокировку
    if cache.get("renew_prices_task_lock"):
        cache.delete("renew_prices_task_lock")
    return JsonResponse({"status": result.state, "result": str(result.result)})


def download_prices(request):
    if request.method != "POST":
        return HttpResponse("Метод не поддерживается.", status=405)

    dir_path = BASE_DIR / os.getenv("OUTPUT_DIR", "output_prices")
    file_path = dir_path / "sorted_brands_output.xlsx"

    if not file_path.exists():
        logger.error("Файл для скачивания не найден по пути: %s", file_path)
        return redirect("/perfume/pricelist/")

    try:
        with file_path.open("rb") as f:
            response = HttpResponse(
                f.read(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = 'attachment; filename="price_file.xlsx"'
            return response
    except Exception as e:
        logger.exception(f"Ошибка при загрузке файла: {e}")
        raise Http404(e)


@staff_member_required
def admin_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, "admin/perfume/order/detail.html", {"order": order})


import base64
import json

@staff_member_required
def invoice_file_proxy(request, receipt_id):
    """
    Обеспечивает доступ к файлам через обычный media URL
    """
    receipt = get_object_or_404(Receipt, id=receipt_id)
    
    if not receipt.invoice_file:
        return HttpResponseForbidden("Файл не найден")
    
    try:
        # Используем стандартный media путь
        relative_path = receipt.invoice_file.name  # например: receipts/invoices/2025/07/IMG_9880.PNG
        local_file_path = Path(settings.BASE_DIR) / 'media' / relative_path
        
        # Проверяем, есть ли файл локально
        if local_file_path.exists():
            # Файл есть - редирект на обычный media URL
            media_url = f"/media/{relative_path}"
            logger.info(f"Файл найден локально: {relative_path}")
            return HttpResponseRedirect(media_url)
        else:
            # Файла нет - скачиваем с S3
            logger.info(f"Скачиваем файл с S3: {relative_path}")
            
            # Создаем папки
            local_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                # Скачиваем с S3
                s3_url = receipt.invoice_file.url
                result = subprocess.run([
                    'curl', '-s', '-L', '--max-time', '30', 
                    '-o', str(local_file_path), s3_url
                ], capture_output=True, timeout=35)
                
                if result.returncode == 0 and local_file_path.exists():
                    logger.info(f"Файл скачан: {relative_path}")
                    media_url = f"/media/{relative_path}"
                    return HttpResponseRedirect(media_url)
                else:
                    logger.error(f"Ошибка скачивания: {result.stderr}")
                    # Fallback на прямую S3 ссылку
                    return HttpResponseRedirect(receipt.invoice_file.url)
                    
            except Exception as e:
                logger.error(f"Ошибка скачивания: {e}")
                return HttpResponseRedirect(receipt.invoice_file.url)
                
    except Exception as e:
        logger.error(f"Ошибка обработки файла: {e}")
        return HttpResponseRedirect(receipt.invoice_file.url)


