from django.apps import AppConfig

from . import __version__


class LinkCheckConfig(AppConfig):
    name = "linkcheck"
    label = "linkcheck"
    verbose_name = f"Link Check v{__version__}"
    default_auto_field = "django.db.models.AutoField"
