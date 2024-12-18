# Официальный базовый Docker-образ Python
FROM python:3.12.5

# Переменные среды
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Рабочий каталог
WORKDIR /code

# Установка зависимостей
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install -r requirements.txt

# Копируем проект
COPY . .