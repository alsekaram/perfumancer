import os
import sys
from celery import Celery

env = os.getenv('DJANGO_SETTINGS_MODULE', 'perfumancer.settings.local')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', env)

app = Celery('perfumancer')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
