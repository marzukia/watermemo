"""API endpoint tests."""

import json

import pytest


@pytest.mark.django_db
class TestHealthEndpoint:
    def test_health(self, api_client):
        res = api_client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["db"] == "ok"
        assert "version" in data


@pytest.mark.django_db
class TestMemoryCRUD:
    def test_create_memory(self, api_client):
        res = api_client.post(
            "/api/memories/",
            data=json.dumps({"content": "test content", "user_id": "u1"}),
            content_type="application/json",
        )
        assert res.status_code == 201
        data = res.json()
        assert data["content"] == "test content"
        assert data["user_id"] == "u1"
        assert "id" in data

    def test_create_memory_returns_fast(self, api_client):
        import time

        start = time.monotonic()
        res = api_client.post(
            "/api/memories/",
            data=json.dumps({"content": "quick test"}),
            content_type="application/json",
        )
        elapsed = time.monotonic() - start
        assert res.status_code == 201
        assert elapsed < 2.0

    def test_list_memories(self, api_client, memory):
        res = api_client.get("/api/memories/")
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 1
        assert any(m["id"] == memory.id for m in data)

    def test_list_memories_filtered_by_user(self, api_client, memory, other_user_memory):
        res = api_client.get("/api/memories/?user_id=test-user-1")
        data = res.json()
        assert all(m["user_id"] == "test-user-1" for m in data)

    def test_get_memory(self, api_client, memory):
        res = api_client.get(f"/api/memories/{memory.id}")
        assert res.status_code == 200
        assert res.json()["id"] == memory.id

    def test_get_memory_404(self, api_client):
        res = api_client.get("/api/memories/99999")
        assert res.status_code == 404

    def test_update_memory(self, api_client, memory):
        res = api_client.patch(
            f"/api/memories/{memory.id}",
            data=json.dumps({"content": "updated"}),
            content_type="application/json",
        )
        assert res.status_code == 200
        assert res.json()["content"] == "updated"

    def test_delete_memory(self, api_client, memory):
        res = api_client.delete(f"/api/memories/{memory.id}")
        assert res.status_code == 204

    def test_delete_all_memories_scoped(self, api_client, memory, other_user_memory):
        res = api_client.delete("/api/memories/?user_id=test-user-1")
        assert res.status_code == 204
        from core.models import Memory

        assert Memory.objects.filter(user_id="test-user-1").count() == 0
        assert Memory.objects.filter(user_id="test-user-2").count() == 1


@pytest.mark.django_db
class TestDistillationCRUD:
    def test_list_distillations(self, api_client, distillation):
        res = api_client.get("/api/distillations/")
        assert res.status_code == 200
        assert len(res.json()) >= 1

    def test_create_distillation(self, api_client, memory):
        res = api_client.post(
            "/api/distillations/",
            data=json.dumps({"content": "manual distillation", "memory_id": memory.id}),
            content_type="application/json",
        )
        assert res.status_code == 201
        assert res.json()["memory_id"] == memory.id

    def test_update_distillation(self, api_client, distillation):
        res = api_client.patch(
            f"/api/distillations/{distillation.id}",
            data=json.dumps({"content": "fixed"}),
            content_type="application/json",
        )
        assert res.status_code == 200
        assert res.json()["content"] == "fixed"

    def test_delete_distillation(self, api_client, distillation):
        res = api_client.delete(f"/api/distillations/{distillation.id}")
        assert res.status_code == 204


@pytest.mark.django_db
class TestDistillationSearch:
    def test_search_returns_results(self, api_client, distillation):
        res = api_client.post(
            "/api/distillations/search",
            data=json.dumps({"query": "sky colour", "limit": 5, "threshold": 2.0}),
            content_type="application/json",
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 1
        assert data[0]["content"] == "The sky is blue."

    def test_search_user_scoped(self, api_client, distillation, other_user_memory):
        res = api_client.post(
            "/api/distillations/search",
            data=json.dumps({
                "query": "anything",
                "limit": 10,
                "threshold": 2.0,
                "user_id": "test-user-2",
            }),
            content_type="application/json",
        )
        data = res.json()
        # Should only return test-user-2's distillation
        for item in data:
            from core.models import Memory

            mem = Memory.objects.get(pk=item["memory_id"])
            assert mem.user_id == "test-user-2"

    def test_search_threshold_filters(self, api_client, distillation):
        # With threshold=0.0, nothing should match (distance > 0)
        res = api_client.post(
            "/api/distillations/search",
            data=json.dumps({"query": "sky", "limit": 5, "threshold": 0.0}),
            content_type="application/json",
        )
        assert res.json() == []
