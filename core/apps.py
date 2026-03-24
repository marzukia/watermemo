from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self) -> None:
        import core.signals  # noqa: F401

        # Warm the cached OpenAI clients so their SSL contexts are created
        # before worker threads start (avoids a race in Python 3.14's
        # SSLContext.__new__).
        from core.integration import embed_client, llm_client

        llm_client()
        embed_client()
