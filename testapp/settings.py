# -*- coding: utf-8 -*-
import os

SITE_NAME = "testapp"

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LOCAL_CACHE_ROOT = "cache"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_commander",
    "testapp",
]

TEMPLATES = []

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": "postgres",
        "USER": "postgres",
        "PASSWORD": "",
        "HOST": "localhost",
        "PORT": "",
    }
}

SECRET_KEY = "testing"

ROOT_URLCONF = __name__

ROOT_URLCONF = "testapp.urls"

WSGI_APPLICATION = "testapp.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

LOGIN_URL = "/login"
LOGIN_REDIRECT_URL = "/"
LOGIN_ERROR_URL = "/login"
AUTHENTICATION_BACKENDS = ("django.contrib.auth.backends.ModelBackend",)

MEDIA_URL = "/media/"
ADMIN_MEDIA_PREFIX = "/media/admin/"
STATIC_URL = "/static/"
STATICFILES_DIRS = []
STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
)


### DJANGO_COMMANDER SETTINGS

DJANGO_COMMANDER_COMMAND_FOLDERS = [
    os.path.abspath(os.path.join(BASE_DIR, "testapp", "commands")).replace("\\", "/")
]
DJANGO_COMMANDER_USE_S3 = False
DEBUG = True
