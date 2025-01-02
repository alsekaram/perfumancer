from celery import shared_task

from .services import update_prices


@shared_task
def update_prices_task():
    # Переносим сюда логику из update_prices()
    update_prices()

    return True