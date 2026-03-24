"""Model tests."""

import pytest
from core.models import Distillation, Memory


@pytest.mark.django_db
class TestMemory:
    def test_create_memory(self):
        mem = Memory.objects.create(content="hello world", user_id="u1")
        assert mem.id is not None
        assert mem.content == "hello world"
        assert mem.user_id == "u1"

    def test_default_user_id_is_blank(self):
        mem = Memory.objects.create(content="no user")
        assert mem.user_id == ""

    def test_str_truncation(self):
        short = Memory(content="short")
        assert str(short) == "short"

        long_content = "x" * 100
        long_mem = Memory(content=long_content)
        assert str(long_mem).endswith("...")
        assert len(str(long_mem)) == 61  # "MEMORY: " (8) + 50 chars + "..." (3)

    def test_ordering_newest_first(self):
        m1 = Memory.objects.create(content="first")
        m2 = Memory.objects.create(content="second")
        ids = list(Memory.objects.values_list("id", flat=True))
        assert ids[0] == m2.id
        assert ids[1] == m1.id


@pytest.mark.django_db
class TestDistillation:
    def test_create_distillation(self, memory):
        dist = Distillation.objects.create(
            content="Summary", memory=memory, is_core=False
        )
        assert dist.memory_id == memory.id
        assert dist.is_core is False

    def test_cascade_delete(self, memory):
        Distillation.objects.create(content="d1", memory=memory)
        assert Distillation.objects.filter(memory=memory).count() == 1
        memory.delete()
        assert Distillation.objects.count() == 0

    def test_related_name(self, memory):
        Distillation.objects.create(content="d1", memory=memory)
        Distillation.objects.create(content="d2", memory=memory)
        assert memory.distillations.count() == 2
