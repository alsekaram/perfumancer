# Perfumancer

**Perfumancer** — Django-приложение, которое автоматизирует обработку прайс-листов и упрощает поиск наиболее дешевых товаров.

## Основные возможности

- **Панель управления товарами**: просмотр списка товаров с указанием поставщика, бренда, названия и цены в долларах. Данные обновляются автоматически. Если цены в прайсе указаны в рублях конвертация в USD производится автоматически
- **Обработка прайс-листов**: система собирает Excel-вложения из писем за последние N дней, анализирует их и фиксирует ключевые параметры (название товара, бренд, цена).
- **Обновляемые данные**: кнопка «Обновить» удаляет старые данные и заново загружает актуальные из почты.
- **Поиск и сортировка**: фильтрация товаров по параметрам и сортировка по столбцам.

## Установка

1. Склонировать проект:
   ```bash
   git clone https://github.com/alsekaram/perfumancer
   cd perfumancer
   ```
2. Настроить файл `.env`:
   ```bash
   cp .env.example .env
   ```

3. Задать права для проекта:
   ```bash
   sudo chown -R www-data:www-data .
   ```

## Запуск через Docker

1. Запустите команду:
   ```bash
   docker-compose up --build
   ```


2. Выполните команды внутри контейнера для подготовки приложения:
   ```bash
   docker-compose exec web python /code/perfumancer/manage.py collectstatic
   docker-compose exec web python /code/perfumancer/manage.py migrate
   docker-compose exec web python /code/perfumancer/manage.py createsuperuser
   ```
3. Откройте приложение по адресу `http://localhost`.

---

## Контакты

Вопросы? [git@awl.su](mailto:git@awl.su)