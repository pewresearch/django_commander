import pkgutil, importlib, re

from django.conf import settings

from pewtils import extract_attributes_from_folder_modules


def get_project_commands():

    return extract_attributes_from_folder_modules(settings.COMMAND_DIR, "Command", include_subdirs=True, concat_subdir_names=True)


class MissingDependencyException(Exception):
    pass