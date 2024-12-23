import logging
import os
from pathlib import Path

from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse, Http404
from django.shortcuts import redirect
from django.urls import reverse

from .services.simple_parser import main as update_prices_service


logger = logging.getLogger(__name__)

def renew_prices(request):
    # Логика для обновления прайс-листов
    update_prices()
    # После выполнения перенаправляем на страницу списка объектов
    return redirect('/perfume/pricelist/')


def update_prices():
    # Логика обновления прайс-листов
    logging.info("Обновление прайс-листов...")
    result = update_prices_service()
    if result:
        logging.info("✅ Прайс-листы успешно обновлены.")
    else:
        logging.error("❌ Обновление прайс-листов не удалось.")


def download_prices(request):
    if request.method != "POST":
        return HttpResponse("Метод не поддерживается.", status=405)

    dir_path = Path(os.getenv("SAVE_DIR", "."))
    file_path = dir_path / "combined_price_list_melted.xlsx"

    if not file_path.exists():
        logger.warning(f"Файл {file_path} не найден.")
        return redirect('/perfume/pricelist/')

    try:
        with file_path.open('rb') as f:
            response = HttpResponse(
                f.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename="price_file.xlsx"'
            return response
    except Exception as e:
        logger.error(f"Ошибка при скачивании файла: {e}")
        raise Http404("Ошибка при загрузке файла.")
