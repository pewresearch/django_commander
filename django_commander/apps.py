import os
from django.apps import AppConfig


DJANGO_COMMANDER_BASE_DIR = os.path.dirname(os.path.realpath(__file__))

class DjangoCommanderConfig(AppConfig):
    name = 'django_commander'

    def update_settings(self):

        from django.conf import settings
        for setting, default in [
            ("DJANGO_COMMANDER_COMMAND_FOLDERS", []),
            ("AWS_ACCESS_KEY_ID", None),
            ("AWS_SECRET_ACCESS_KEY", None),
            ("S3_BUCKET", None),
            ("LOCAL_CACHE_ROOT", "cache"),
            ("S3_CACHE_ROOT", "cache"),
            ("DJANGO_COMMANDER_USE_S3", False)
        ]:
            if not hasattr(settings, setting):
                setattr(settings, setting, default)

        LOCAL_CACHE_PATH = os.path.join(settings.LOCAL_CACHE_ROOT, "django_queries")
        setattr(settings, "LOCAL_CACHE_PATH", LOCAL_CACHE_PATH)
        if settings.DJANGO_COMMANDER_USE_S3:
            S3_CACHE_PATH = os.path.join(settings.S3_CACHE_ROOT, "django_queries")
        else:
            S3_CACHE_PATH = settings.LOCAL_CACHE_PATH
        setattr(settings, "S3_CACHE_PATH", S3_CACHE_PATH)

        templates = settings.TEMPLATES
        new_templates = []
        for template in templates:
            template["DIRS"].append(os.path.join(DJANGO_COMMANDER_BASE_DIR, "templates"))
            new_templates.append(template)
        setattr(settings, "TEMPLATES", new_templates)

    def __init__(self, *args, **kwargs):
        super(DjangoCommanderConfig, self).__init__(*args, **kwargs)
        self.update_settings()

    def ready(self):
        self.update_settings()