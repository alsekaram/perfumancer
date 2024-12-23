import logging

from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse

from .services.simple_parser import main as update_prices_service


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
