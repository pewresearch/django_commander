# -*- coding: utf-8 -*-
import os

from django.conf import settings
from django.db import models

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
# Copied from django_extensions as a boilerplate example
# REPLACEMENTS = {
# }
# add_replacements = getattr(settings, 'EXTENSIONS_REPLACEMENTS', {})
# REPLACEMENTS.update(add_replacements)

from django.db import models

if not getattr(settings, 'DJANGO_COMMANDER_COMMAND_FOLDERS', None):
    DJANGO_COMMANDER_COMMAND_FOLDERS = []
if not getattr(settings, 'DJANGO_COMMANDER_BASE_MODEL', None):
    # DJANGO_COMMANDER_BASE_MODEL = models.Model
    from pewtils.django.abstract_models import BasicExtendedModel
    DJANGO_COMMANDER_BASE_MODEL = BasicExtendedModel
if not getattr(settings, 'DJANGO_COMMANDER_BASE_MANAGER', None):
    from pewtils.django.managers import BasicManager
    DJANGO_COMMANDER_BASE_MANAGER = BasicManager
    # LOADER_BASE_MANAGER = models.QuerySet