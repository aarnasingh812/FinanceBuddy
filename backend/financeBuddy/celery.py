"""
Celery application instance for the FinanceBuddy project.

Start the worker with:
    celery -A financeBuddy worker --loglevel=info --pool=solo 
"""

import os
from celery import Celery

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'financeBuddy.settings')

app = Celery('financeBuddy')

# Read config from Django settings; all Celery keys must start with CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks.py in each installed app
app.autodiscover_tasks()
