from django.core.cache import cache
from django.http import JsonResponse, HttpResponse, Http404
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required

from .tasks import update_prices_task
from .models import Order

from celery.result import AsyncResult
from pathlib import Path
import os
import logging

logger = logging.getLogger(__name__)


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

    dir_path = Path("./" + os.getenv("OUTPUT_DIR", "."))
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
