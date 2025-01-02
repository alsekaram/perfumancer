from celery import shared_task
from django.core.cache import cache
from .services import update_prices

@shared_task
def update_prices_task():
    try:
        update_prices()
    finally:
        cache.delete('renew_prices_task_lock')  # Убираем блокировку после завершения
    return True
