from .base import *

DEBUG = True


CSRF_TRUSTED_ORIGINS = [
    "https://c149-116-203-69-235.ngrok-free.app",
]

ALLOWED_HOSTS = ["*"]


DATABASES = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}
}

CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_RESULT_EXPIRES = 3600
