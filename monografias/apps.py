from django.apps import AppConfig


class MonografiasConfig(AppConfig):
    name = 'monografias'

    def ready(self):
        from . import signals  # noqa: F401
