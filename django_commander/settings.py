# -*- coding: utf-8 -*-
import os

from django.conf import settings

from pewtils.django.abstract_models import BasicExtendedModel
from pewtils.django.managers import BasicManager


BASE_DIR = os.path.dirname(os.path.realpath(__file__))

for setting, default in [
    ("DJANGO_COMMANDER_COMMAND_FOLDERS", []),
    ("DJANGO_COMMANDER_BASE_MODEL", BasicExtendedModel),
    ("DJANGO_COMMANDER_BASE_MANAGER", BasicManager)
]:
    if not getattr(settings, setting, None):
        globals()[setting] = default