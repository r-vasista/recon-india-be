from __future__ import absolute_import
import os
import logging.config
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recon.settings')

logging.config.dictConfig(settings.LOGGING)

app = Celery('recon')

# Namespace tells Celery to read settings prefixed with CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all apps
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
