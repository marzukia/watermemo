"""Background task tests."""

import pytest
from unittest.mock import patch, MagicMock

# close_old_connections() kills the test DB connection; patch it out.
_CLC = "django.db.close_old_connections"


@pytest.mark.django_db
class TestDistillTask:
    @patch(_CLC)
    def test_distill_creates_distillation(self, _clc, memory):
        from core.models import Distillation
        from core.tasks import _distill_memory_sync

        _distill_memory_sync(memory.id)
        dist = Distillation.objects.filter(memory=memory).first()
        assert dist is not None
        assert dist.content == "Mocked distillation summary."

    @patch(_CLC)
    def test_distill_no_memory_skips(self, _clc, memory, monkeypatch):
        monkeypatch.setattr(
            "core.integration.chat",
            lambda question, system_prompt=None: "no_memory",
        )
        from core.models import Distillation
        from core.tasks import _distill_memory_sync

        _distill_memory_sync(memory.id)
        assert Distillation.objects.filter(memory=memory).count() == 0

    def test_distill_missing_memory(self):
        from core.tasks import _distill_memory_sync

        # Should log but not crash
        _distill_memory_sync(999999)


@pytest.mark.django_db
class TestRedistillTask:
    @patch(_CLC)
    def test_redistill_deletes_old_and_creates_new(self, _clc, memory, distillation):
        from core.models import Distillation
        from core.tasks import _redistill_memory_sync

        old_id = distillation.id
        _redistill_memory_sync(memory.id)

        # Old distillation should be gone
        assert not Distillation.objects.filter(id=old_id).exists()
        # New one should exist
        new = Distillation.objects.filter(memory=memory).first()
        assert new is not None
        assert new.id != old_id

    def test_redistill_missing_memory(self):
        from core.tasks import _redistill_memory_sync

        _redistill_memory_sync(999999)


@pytest.mark.django_db
class TestSubmitFunctions:
    def test_submit_distill_does_not_block(self, memory):
        import time

        from core.tasks import submit_distill

        start = time.monotonic()
        submit_distill(memory.id)
        elapsed = time.monotonic() - start
        assert elapsed < 0.1  # Should be near-instant
