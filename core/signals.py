from collections.abc import Iterable

from django.contrib.postgres.search import SearchVector
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.integration import embed

from .models import Distillation, Memory


def _update_sv(
    sender: type, instance: object, update_fields: Iterable[str] | None
) -> None:
    """Update the SearchVectorField for a BaseMemory instance after save."""
    if update_fields is not None and "content" not in update_fields:
        return
    sender.objects.filter(pk=instance.pk).update(  # type: ignore[attr-defined]
        sv=SearchVector("content", config="english"),
    )


def _update_embedding(
    sender: type, instance: object, update_fields: Iterable[str] | None
) -> None:
    """Generate and store an embedding vector for a BaseMemory instance after save."""
    if update_fields is not None and "content" not in update_fields:
        return
    content = getattr(instance, "content", None)
    if not content:
        return
    vector = embed(content)
    sender.objects.filter(pk=getattr(instance, "pk")).update(  # type: ignore[attr-defined]
        embedding=vector,
    )


@receiver(post_save, sender=Memory)
def populate_memory_fields(
    sender: type[Memory],
    instance: Memory,
    **kwargs: object,
) -> None:
    update_fields: Iterable[str] | None = kwargs.get("update_fields")  # type: ignore[assignment]
    _update_sv(sender, instance, update_fields)
    _update_embedding(sender, instance, update_fields)


@receiver(post_save, sender=Distillation)
def populate_distillation_fields(
    sender: type[Distillation],
    instance: Distillation,
    **kwargs: object,
) -> None:
    update_fields: Iterable[str] | None = kwargs.get("update_fields")  # type: ignore[assignment]
    _update_sv(sender, instance, update_fields)
    _update_embedding(sender, instance, update_fields)
