from django.apps import AppConfig


class PerfumeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "perfume"

    def ready(self):
        import perfume.signals  # Регистрация сигналов
