# -*- coding: utf-8 -*-
import os

from django.conf import settings


BASE_DIR = os.path.dirname(os.path.realpath(__file__))

for setting, default in [
    ("DJANGO_COMMANDER_COMMAND_FOLDERS", [])
]:
    if not getattr(settings, setting, None):
        globals()[setting] = default
    else:
        globals()[setting] = getattr(settings, setting)

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, 'templates')],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages'
            ]
        }
    }
]