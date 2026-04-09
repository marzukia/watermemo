"""Security-focused tests for vulnerabilities fixed in this PR."""

import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# Path traversal in load_prompt
# ---------------------------------------------------------------------------


class TestLoadPromptPathTraversal:
    def test_valid_prompt_loads(self):
        from core.integration import load_prompt

        text = load_prompt("DISTILLATION")
        assert len(text) > 0

    def test_path_traversal_blocked(self):
        from core.integration import load_prompt

        with pytest.raises(ValueError, match="Invalid prompt name"):
            load_prompt("../../settings")

    def test_absolute_path_blocked(self):
        from core.integration import load_prompt

        with pytest.raises(ValueError, match="Invalid prompt name"):
            load_prompt("/etc/passwd")

    def test_null_byte_blocked(self):
        from core.integration import load_prompt

        # Null bytes in filenames are rejected by the OS (OSError/ValueError);
        # either indicates the path traversal attempt was blocked.
        with pytest.raises((ValueError, OSError)):
            load_prompt("DISTILLATION\x00../settings")


# ---------------------------------------------------------------------------
# Input size limits (schemas)
# ---------------------------------------------------------------------------


class TestInputSizeLimits:
    def test_memory_in_rejects_oversized_content(self):
        from core.schemas import MemoryIn

        with pytest.raises(ValidationError):
            MemoryIn(content="x" * 65_537)

    def test_memory_in_accepts_max_length(self):
        from core.schemas import MemoryIn

        m = MemoryIn(content="x" * 65_536)
        assert len(m.content) == 65_536

    def test_memory_in_rejects_oversized_user_id(self):
        from core.schemas import MemoryIn

        with pytest.raises(ValidationError):
            MemoryIn(content="hello", user_id="u" * 256)

    def test_distillation_in_rejects_oversized_content(self):
        from core.schemas import DistillationIn

        with pytest.raises(ValidationError):
            DistillationIn(content="x" * 65_537, memory_id=1)

    def test_search_query_rejects_oversized_query(self):
        from core.schemas import SearchQuery

        with pytest.raises(ValidationError):
            SearchQuery(query="q" * 65_537)

    def test_classify_query_rejects_oversized_text(self):
        from core.schemas import ClassifyQuery

        with pytest.raises(ValidationError):
            ClassifyQuery(text="t" * 65_537)

    def test_recall_query_rejects_oversized_query(self):
        from core.schemas import RecallQuery

        with pytest.raises(ValidationError):
            RecallQuery(query="q" * 65_537)


# ---------------------------------------------------------------------------
# API key authentication
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestApiKeyAuthentication:
    """When API_KEY is set every protected endpoint requires the bearer token."""

    def test_health_is_public(self, api_client, settings):
        """Health endpoint must remain accessible without a key."""
        settings.API_KEY = "secret-key"
        res = api_client.get("/api/health")
        assert res.status_code == 200

    def test_protected_endpoint_requires_key(self, api_client, settings):
        """Without a token a 401 is returned when API_KEY is configured."""
        settings.API_KEY = "secret-key"
        res = api_client.get("/api/memories/")
        assert res.status_code == 401

    def test_protected_endpoint_accepts_valid_key(self, api_client, settings):
        """A correct bearer token grants access."""
        settings.API_KEY = "secret-key"
        res = api_client.get(
            "/api/memories/",
            HTTP_AUTHORIZATION="Bearer secret-key",
        )
        assert res.status_code == 200

    def test_protected_endpoint_rejects_wrong_key(self, api_client, settings):
        """A wrong bearer token returns 401."""
        settings.API_KEY = "secret-key"
        res = api_client.get(
            "/api/memories/",
            HTTP_AUTHORIZATION="Bearer wrong-key",
        )
        assert res.status_code == 401

    def test_no_key_configured_allows_access(self, api_client, settings):
        """When API_KEY is empty all traffic is allowed (backward-compatible)."""
        settings.API_KEY = ""
        res = api_client.get("/api/memories/")
        assert res.status_code == 200
