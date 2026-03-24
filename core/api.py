import json
import math
import tomllib
from http import HTTPStatus
from pathlib import Path

from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from ninja import NinjaAPI, Router
from pgvector.django import CosineDistance

from .integration import load_prompt
from .models import Distillation, Memory
from .schemas import (
    DistillationIn,
    DistillationOut,
    DistillationUpdate,
    MemoryIn,
    MemoryOut,
    MemoryUpdate,
    ClassifyOut,
    ClassifyQuery,
    RecallMemoryContext,
    RecallOut,
    RecallQuery,
    SearchQuery,
    SearchResultOut,
)

api = NinjaAPI(title="watermemo API")
memory_router = Router()
distillation_router = Router()


@api.get("/health")
def health(request) -> dict[str, str]:
    """Return service health status and current version."""
    from django.db import connection

    try:
        connection.ensure_connection()
        db_status = "ok"
    except Exception as exc:
        db_status = f"error: {exc}"

    try:
        _pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
        app_version = tomllib.loads(_pyproject.read_text())["project"]["version"]
    except Exception:
        app_version = "unknown"

    overall = "ok" if db_status == "ok" else "degraded"
    return {"status": overall, "version": app_version, "db": db_status}


@memory_router.get("/", response=list[MemoryOut])
def list_memories(request) -> list[Memory]:
    return list(Memory.objects.all())


@memory_router.post("/", response={HTTPStatus.CREATED: MemoryOut})
def create_memory(request, payload: MemoryIn) -> tuple[int, Memory]:
    """Create a memory and automatically generate a distillation via LLM."""
    memory = Memory.objects.create(content=payload.content)
    Distillation.objects.distill(memory)
    return HTTPStatus.CREATED, memory


@memory_router.get("/{memory_id}", response=MemoryOut)
def get_memory(request, memory_id: int) -> Memory:
    return get_object_or_404(Memory, id=memory_id)


@memory_router.patch("/{memory_id}", response=MemoryOut)
def update_memory(request, memory_id: int, payload: MemoryUpdate) -> Memory:
    memory = get_object_or_404(Memory, id=memory_id)
    updated = payload.dict(exclude_unset=True)
    for field, value in updated.items():
        setattr(memory, field, value)
    memory.save(update_fields=list(updated.keys()))
    return memory


@memory_router.delete("/{memory_id}", response={HTTPStatus.NO_CONTENT: None})
def delete_memory(request, memory_id: int) -> tuple[int, None]:
    get_object_or_404(Memory, id=memory_id).delete()
    return HTTPStatus.NO_CONTENT, None


@memory_router.delete("/", response={HTTPStatus.NO_CONTENT: None})
def delete_all_memories(request) -> tuple[int, None]:
    """Delete every memory and its associated distillations."""
    Memory.objects.all().delete()
    return HTTPStatus.NO_CONTENT, None


@distillation_router.get("/", response=list[DistillationOut])
def list_distillations(request) -> list[Distillation]:
    return list(Distillation.objects.select_related("memory").all())


@distillation_router.post("/", response={HTTPStatus.CREATED: DistillationOut})
def create_distillation(request, payload: DistillationIn) -> tuple[int, Distillation]:
    memory = get_object_or_404(Memory, id=payload.memory_id)
    distillation = Distillation.objects.create(content=payload.content, memory=memory)
    return HTTPStatus.CREATED, distillation


@distillation_router.get("/{distillation_id}", response=DistillationOut)
def get_distillation(request, distillation_id: int) -> Distillation:
    return get_object_or_404(Distillation, id=distillation_id)


@distillation_router.patch("/{distillation_id}", response=DistillationOut)
def update_distillation(
    request, distillation_id: int, payload: DistillationUpdate
) -> Distillation:
    distillation = get_object_or_404(Distillation, id=distillation_id)
    updated = payload.dict(exclude_unset=True)
    for field, value in updated.items():
        setattr(distillation, field, value)
    distillation.save(update_fields=list(updated.keys()))
    return distillation


@distillation_router.delete(
    "/{distillation_id}", response={HTTPStatus.NO_CONTENT: None}
)
def delete_distillation(request, distillation_id: int) -> tuple[int, None]:
    get_object_or_404(Distillation, id=distillation_id).delete()
    return HTTPStatus.NO_CONTENT, None


api.add_router("/memories", memory_router)
api.add_router("/distillations", distillation_router)


@api.post("/distillations/search", response=list[SearchResultOut])
def search_distillations(request, payload: SearchQuery) -> list[dict]:
    """Search distillations by vector similarity. Returns results ordered by cosine distance."""
    from core.integration import embed

    query_vector = embed(payload.query)
    results = (
        Distillation.objects.filter(embedding__isnull=False)
        .annotate(distance=CosineDistance("embedding", query_vector))
        .filter(distance__lt=payload.threshold)
        .order_by("distance")[: payload.limit]
    )
    return [
        {
            "id": d.id,
            "content": d.content,
            "memory_id": d.memory_id,
            "is_core": d.is_core,
            "distance": d.distance,
        }
        for d in results
    ]


@api.post("/classify", response=ClassifyOut)
def classify(request, payload: ClassifyQuery) -> dict:
    """
    Classify the intent of a user message with respect to memory management.
    Returns intent: 'delete' | 'store' | 'ignore' and confidence: 'high' | 'low'.
    """
    from core.integration import chat

    raw = chat(payload.text, system_prompt=load_prompt("CLASSIFY")) or ""
    import json as _json
    import re as _re
    # Strip markdown code fences that some models wrap around JSON
    stripped = _re.sub(r"```[a-z]*\n?", "", raw).strip().strip("`").strip()
    try:
        result = _json.loads(stripped)
        intent = result.get("intent", "ignore")
        confidence = result.get("confidence", "low")
        scope = result.get("scope", "specific")
        if intent not in ("delete", "store", "ignore"):
            intent = "ignore"
        if confidence not in ("high", "low"):
            confidence = "low"
        if scope not in ("all", "specific"):
            scope = "specific"
        recall = bool(result.get("recall", True))
    except Exception:
        intent, confidence, scope, recall = "ignore", "low", "specific", True
    return {"intent": intent, "confidence": confidence, "scope": scope, "recall": recall}


@api.post("/recall", response=RecallOut)
def recall(request, payload: RecallQuery) -> dict:
    """
    Distillation-first RAG recall.

    Embeds the query, finds the closest distillations by cosine distance,
    resolves the full Memory content via FK, then passes context to the LLM.
    """
    from core.integration import chat, embed

    query_vector = embed(payload.query)
    now = __import__("django.utils.timezone", fromlist=["now"]).now()

    def decayed_distance(d: Distillation) -> float:
        """Apply exponential decay penalty based on memory age."""
        if not payload.decay_half_life_days:
            return d.distance  # type: ignore[attr-defined]
        age_days = (now - d.memory.created_datetime).total_seconds() / 86400
        decay = math.exp(math.log(2) / payload.decay_half_life_days * age_days)
        return d.distance * decay  # type: ignore[attr-defined]

    base_qs = (
        Distillation.objects.select_related("memory")
        .filter(embedding__isnull=False)
        .annotate(distance=CosineDistance("embedding", query_vector))
    )

    # Core memories — always fetched with a loose threshold (2x normal)
    core_distillations = list(
        base_qs.filter(is_core=True)
        .filter(distance__lt=payload.threshold * 2)
        .order_by("distance")[:payload.limit]
    )

    # Regular memories — fill remaining slots
    regular_slots = payload.limit - len(core_distillations)
    core_ids = {d.id for d in core_distillations}
    regular_distillations = []
    if regular_slots > 0:
        regular_distillations = list(
            base_qs.filter(is_core=False)
            .filter(distance__lt=payload.threshold)
            .exclude(id__in=core_ids)
            .order_by("distance")[: regular_slots * 3]
        )
        regular_distillations.sort(key=decayed_distance)
        regular_distillations = regular_distillations[:regular_slots]

    # Core first, then regular
    distillations = core_distillations + regular_distillations

    if not distillations:
        return {
            "answer": "No relevant memories found.",
            "memories_used": 0,
            "context": [],
        }

    memory_ids = list({d.memory_id for d in distillations})
    memories = {m.id: m for m in Memory.objects.filter(id__in=memory_ids)}

    context_items: list[RecallMemoryContext] = []
    context_parts: list[str] = []

    for d in distillations:
        memory = memories.get(d.memory_id)
        if not memory:
            continue
        context_items.append(
            RecallMemoryContext(
                id=memory.id,
                content=memory.content,
                distillation=d.content,
                is_core=d.is_core,
                distance=d.distance,
            )
        )
        context_parts.append(
            f"[Memory {len(context_items)}{' (CORE)' if d.is_core else ''}]\n"
            f"Summary: {d.content}\nFull content: {memory.content}"
        )

    answer = chat(
        f"Memories:\n\n{'\n\n'.join(context_parts)}\n\nQuestion: {payload.query}",
        system_prompt=load_prompt("RECALL"),
    )

    return {
        "answer": answer,
        "memories_used": len(context_items),
        "context": context_items,
    }


@api.post("/recall/stream")
def recall_stream(request, payload: RecallQuery):
    """
    Streaming variant of /recall using Server-Sent Events.

    Emits three event types:
    - {type: "context", data: [...]} — retrieved memory metadata, sent first
    - {type: "token", data: "..."} — one event per LLM token
    - {type: "done", memories_used: N} — signals stream completion
    """
    from core.integration import embed, stream_chat

    query_vector = embed(payload.query)
    now = __import__("django.utils.timezone", fromlist=["now"]).now()

    def decayed_distance(d: Distillation) -> float:
        """Apply exponential decay penalty based on memory age."""
        if not payload.decay_half_life_days:
            return d.distance  # type: ignore[attr-defined]
        age_days = (now - d.memory.created_datetime).total_seconds() / 86400
        decay = math.exp(math.log(2) / payload.decay_half_life_days * age_days)
        return d.distance * decay  # type: ignore[attr-defined]

    distillations = list(
        Distillation.objects.select_related("memory")
        .filter(embedding__isnull=False)
        .annotate(distance=CosineDistance("embedding", query_vector))
        .filter(distance__lt=payload.threshold)
        .order_by("distance")[: payload.limit * 3]
    )
    distillations.sort(key=decayed_distance)
    distillations = distillations[: payload.limit]

    if not distillations:

        def _empty():
            yield f"data: {json.dumps({'type': 'context', 'data': []})}\n\n"
            yield f"data: {json.dumps({'type': 'token', 'data': 'No relevant memories found.'})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'memories_used': 0})}\n\n"

        return StreamingHttpResponse(_empty(), content_type="text/event-stream")

    memory_ids = list({d.memory_id for d in distillations})
    memories = {m.id: m for m in Memory.objects.filter(id__in=memory_ids)}

    context_items = []
    context_parts = []

    for d in distillations:
        memory = memories.get(d.memory_id)
        if not memory:
            continue
        context_items.append(
            {
                "id": memory.id,
                "content": memory.content,
                "distillation": d.content,
                "distance": d.distance,
            }
        )
        context_parts.append(
            f"[Memory {len(context_items)}]\nSummary: {d.content}\nFull content: {memory.content}"
        )

    prompt = f"Memories:\n\n{'\n\n'.join(context_parts)}\n\nQuestion: {payload.query}"
    system_prompt = load_prompt("RECALL")
    memories_used = len(context_items)

    def _stream():
        yield f"data: {json.dumps({'type': 'context', 'data': context_items})}\n\n"
        for token in stream_chat(prompt, system_prompt=system_prompt):
            yield f"data: {json.dumps({'type': 'token', 'data': token})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'memories_used': memories_used})}\n\n"

    return StreamingHttpResponse(_stream(), content_type="text/event-stream")
