import logging

from .price_list_services.simple_parser import main as update_prices_service

logger = logging.getLogger(__name__)


def update_prices():
    # Логика обновления прайс-листов
    logging.info("Обновление прайс-листов...")
    result = update_prices_service()
    if result:
        logging.info("✅ Прайс-листы успешно обновлены.")
    else:
        logging.error("❌ Обновление прайс-листов не удалось.")
