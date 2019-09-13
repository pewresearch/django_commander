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

### DJANGO_COMMANDER SETTINGS

DJANGO_COMMANDER_COMMAND_FOLDERS = [
    os.path.abspath(os.path.join(BASE_DIR, "testapp", "commands")).replace('\\', '/')
]
DJANGO_COMMANDER_USE_S3 = False