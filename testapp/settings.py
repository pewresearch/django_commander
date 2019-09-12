# -*- coding: utf-8 -*-
import os

SITE_NAME = "testapp"

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django_commander",
    "testapp"
]

TEMPLATES = []

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'postgres',
        'USER': 'postgres',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '',
    }
}

SECRET_KEY = "testing"

DJANGO_COMMANDER_COMMAND_FOLDERS = [
    os.path.abspath(os.path.join(BASE_DIR, "testapp", "commands")).replace('\\', '/')
]

##### CELERY SETTINGS

# CELERY_BROKER_URL = "redis://localhost:6379"
# BROKER_URL = 'redis://127.0.0.1:6379'
# CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379'
# CELERY_ACCEPT_CONTENT = ["pickle", "json"]
# CELERY_TASK_SERIALIZER = "pickle"
# CELERY_RESULT_SERIALIZER = "pickle"


CELERY_RESULT_BACKEND = 'django-db'
CELERY_BROKER_URL = BROKER_URL = 'amqp://guest:guest@localhost'

if CELERY_BROKER_URL.startswith('sqs://'):
    CELERY_BROKER_TRANSPORT_OPTIONS = {
        'visibility_timeout': 43200,
        'polling_interval': 1.0,
        'queue_name_prefix': 'testapp_'
    }

CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1