from typing import Self

from django.contrib.postgres.search import SearchVectorField
from django.db import models
from pgvector.django import VectorField

from core.integration import chat


class BaseMemory(models.Model):
    """Shared fields for Memory and Distillation."""

    key = "MEMORY"

    id = models.AutoField(primary_key=True)
    content = models.TextField()
    sv = SearchVectorField(null=True)
    embedding = VectorField(dimensions=768, null=True)
    created_datetime = models.DateTimeField(auto_now_add=True)
    updated_datetime = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return (
            f"{self.key}: {self.content[:50]}..."
            if len(self.content) > 50
            else self.content
        )

    class Meta:
        ordering = ["-created_datetime"]
        abstract = True


class Memory(BaseMemory):
    key = "MEMORY"
    user_id = models.CharField(max_length=255, blank=True, default="", db_index=True)


class DistillationManager(models.Manager):
    def distill(self, memory: Memory) -> Self:
        """Distill a Memory via the LLM."""
        from core.integration import load_prompt

        mem, _ = Memory.objects.get_or_create(content=memory.content)
        system_prompt = load_prompt("DISTILLATION")
        distillation_text = chat(memory.content, system_prompt=system_prompt)

        # Evaluate whether this is a core memory
        core_prompt = load_prompt("CORE_EVAL")
        core_raw = (chat(memory.content, system_prompt=core_prompt) or "").strip().lower()
        is_core = core_raw.startswith("true")

        return self.create(content=distillation_text, memory=mem, is_core=is_core)


class Distillation(BaseMemory):
    key = "DISTILLATION"

    memory = models.ForeignKey(
        Memory,
        on_delete=models.CASCADE,
        related_name="distillations",
    )
    is_core = models.BooleanField(default=False)

    objects: DistillationManager = DistillationManager()  # type: ignore[assignment]
