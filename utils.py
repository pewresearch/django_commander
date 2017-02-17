import pkgutil, importlib, re

from django.conf import settings


def get_project_loaders():

    name_split = settings.LOADER_DIR.split(settings.SITE_NAME)
    name = settings.SITE_NAME + re.sub(r"[/\\]", '.', name_split[-1])
    path = [settings.LOADER_DIR]
    loaders = {}
    path = pkgutil.extend_path(path, name)
    for importer, modname, ispkg in pkgutil.walk_packages(path=path, prefix=name + '.'):
        if not ispkg:
            module = importlib.import_module(modname)
            if hasattr(module, "Loader"):
                loader = getattr(module, "Loader")
                loaders[loader.name] = loader

    return loaders


class MissingDependencyException(Exception):
    pass