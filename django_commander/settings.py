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