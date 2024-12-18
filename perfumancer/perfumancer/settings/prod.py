from django.conf.global_settings import SESSION_COOKIE_SECURE, SECURE_SSL_REDIRECT, SECURE_HSTS_SECONDS
import os
from dotenv import load_dotenv
from .base import *


load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")

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

CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = False
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_PRELOAD = False
