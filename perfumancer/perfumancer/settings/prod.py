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
