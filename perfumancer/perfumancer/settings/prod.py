from .base import *

DEBUG = False

ADMINS = [
    ('Alex', 'perf@awl.su')
]

ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3'
    }
}

CELERY_BROKER_URL = 'redis://redis:6379/0'
CELERY_RESULT_BACKEND = 'redis://redis:6379/0'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_RESULT_EXPIRES = 3600

