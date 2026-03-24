"""Filter tests (inlet + outlet)."""

import json
import os
import pytest
from unittest.mock import patch, MagicMock

import sys
import importlib.util

FILTER_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "open_webui",
    "filter.py",
)


@pytest.fixture
def filter_cls():
    # Mock 'requests' since it's an Open WebUI runtime dep
    mock_requests = MagicMock()
    sys.modules.setdefault("requests", mock_requests)
    spec = importlib.util.spec_from_file_location("owui_filter", FILTER_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.Filter


@pytest.fixture
def f(filter_cls):
    """Return an instantiated Filter with test valves."""
    instance = filter_cls()
    instance.valves.base_url = "http://test:8000/api"
    return instance


class TestBuildRecallQuery:
    def test_single_user_message(self, f):
        msgs = [{"role": "user", "content": "hello"}]
        assert f._build_recall_query(msgs) == "hello"

    def test_multi_turn_context(self, f):
        msgs = [
            {"role": "user", "content": "Tell me about dogs"},
            {"role": "assistant", "content": "Dogs are great pets."},
            {"role": "user", "content": "What about cats?"},
        ]
        query = f._build_recall_query(msgs)
        assert "dogs" in query.lower()
        assert "What about cats?" in query

    def test_system_messages_excluded(self, f):
        msgs = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "hi"},
        ]
        query = f._build_recall_query(msgs)
        assert "helpful" not in query
        assert query == "hi"

    def test_empty_messages(self, f):
        assert f._build_recall_query([]) == ""

    def test_long_messages_truncated(self, f):
        long_text = "x" * 1000
        msgs = [
            {"role": "user", "content": long_text},
            {"role": "user", "content": "follow-up"},
        ]
        query = f._build_recall_query(msgs)
        # The first (non-last) message should be truncated to 500
        lines = query.split("\n")
        assert len(lines[0]) == 500


class TestDeleteDetection:
    def test_forget_everything(self, f):
        is_del, scope = f._looks_like_delete("Please forget everything")
        assert is_del is True
        assert scope == "all"

    def test_delete_specific(self, f):
        is_del, scope = f._looks_like_delete("Can you forget what I said about cats?")
        assert is_del is True
        assert scope == "specific"

    def test_normal_message(self, f):
        is_del, scope = f._looks_like_delete("What's the weather like?")
        assert is_del is False

    def test_case_insensitive(self, f):
        is_del, _ = f._looks_like_delete("DELETE ALL MEMORIES")
        assert is_del is True


class TestInlet:
    @patch("requests.post")
    def test_inlet_injects_memories(self, mock_post, f):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"content": "User's name is Test.", "is_core": True, "distance": 0.1}
        ]
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        body = {
            "messages": [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "What's my name?"},
            ]
        }
        result = f.inlet(body, {"id": "u1"})

        # System prompt should contain injected memory
        system_msg = [m for m in result["messages"] if m["role"] == "system"][0]
        assert "User's name is Test." in system_msg["content"]

    @patch("requests.post")
    def test_inlet_passes_user_id(self, mock_post, f):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        body = {"messages": [{"role": "user", "content": "hello"}]}
        f.inlet(body, {"id": "my-uuid"})

        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["user_id"] == "my-uuid"

    def test_inlet_disabled(self, f):
        f.valves.enabled = False
        body = {"messages": [{"role": "user", "content": "hi"}]}
        assert f.inlet(body) == body

    @patch("requests.post", side_effect=Exception("connection refused"))
    def test_inlet_handles_errors_gracefully(self, mock_post, f):
        body = {
            "messages": [
                {"role": "system", "content": "base"},
                {"role": "user", "content": "hello"},
            ]
        }
        result = f.inlet(body, {"id": "u1"})
        # Should pass through unchanged on error
        system_msg = [m for m in result["messages"] if m["role"] == "system"][0]
        assert system_msg["content"] == "base"

    @patch("requests.post")
    def test_inlet_sets_think_false(self, mock_post, f):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []
        mock_post.return_value = mock_resp

        body = {
            "messages": [
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "hi"},
            ]
        }
        result = f.inlet(body, {"id": "u1"})
        assert result.get("think") is False


class TestOutlet:
    @patch("requests.post")
    def test_outlet_stores_exchange(self, mock_post, f):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []  # no near-duplicates
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        body = {
            "messages": [
                {"role": "user", "content": "What is Python?"},
                {"role": "assistant", "content": "A programming language."},
            ]
        }
        f.outlet(body, {"id": "u1"})

        # Should have made 2 calls: search + create
        assert mock_post.call_count == 2
        create_call = mock_post.call_args_list[1]
        payload = create_call.kwargs.get("json") or create_call[1].get("json")
        assert "Python" in payload["content"]
        assert payload["user_id"] == "u1"

    @patch("requests.post")
    @patch("requests.delete")
    def test_outlet_delete_all(self, mock_delete, mock_post, f):
        body = {
            "messages": [
                {"role": "user", "content": "forget everything"},
                {"role": "assistant", "content": "Done."},
            ]
        }
        f.outlet(body, {"id": "u1"})
        mock_delete.assert_called_once()

    def test_outlet_disabled(self, f):
        f.valves.enabled = False
        body = {"messages": [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hey"}]}
        assert f.outlet(body) == body

    def test_outlet_caps_long_responses(self, f):
        long_text = "x" * 3000
        body = {
            "messages": [
                {"role": "user", "content": "test"},
                {"role": "assistant", "content": long_text},
            ]
        }
        with patch("requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = []
            mock_resp.raise_for_status = MagicMock()
            mock_post.return_value = mock_resp

            f.outlet(body, {"id": "u1"})

            create_call = mock_post.call_args_list[1]
            payload = create_call.kwargs.get("json") or create_call[1].get("json")
            # Ensure stored content is within bounds
            assert len(payload["content"]) < 2200
