import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def _no_llm_calls(monkeypatch):
    """Stub out LLM and embedding calls."""
    monkeypatch.setattr(
        "core.integration.chat",
        lambda question, system_prompt=None: "Mocked distillation summary.",
    )
    monkeypatch.setattr(
        "core.integration.embed",
        lambda text, model=None: [0.1] * 768,
    )


@pytest.fixture
def memory(db):
    from core.models import Memory

    return Memory.objects.create(
        content="User: What colour is the sky?\nAssistant: Blue.",
        user_id="test-user-1",
    )


@pytest.fixture
def distillation(memory):
    from core.models import Distillation

    return Distillation.objects.create(
        content="The sky is blue.",
        memory=memory,
        is_core=False,
        embedding=[0.1] * 768,
    )


@pytest.fixture
def core_distillation(db):
    from core.models import Distillation, Memory

    mem = Memory.objects.create(
        content="User: My name is Fungus.\nAssistant: Nice to meet you, Fungus!",
        user_id="test-user-1",
    )
    return Distillation.objects.create(
        content="The user's name is Fungus.",
        memory=mem,
        is_core=True,
        embedding=[0.2] * 768,
    )


@pytest.fixture
def other_user_memory(db):
    from core.models import Distillation, Memory

    mem = Memory.objects.create(
        content="User: I like cats.\nAssistant: Cats are great!",
        user_id="test-user-2",
    )
    Distillation.objects.create(
        content="User likes cats.",
        memory=mem,
        is_core=False,
        embedding=[0.3] * 768,
    )
    return mem


@pytest.fixture
def api_client():
    from django.test import Client

    return Client()
