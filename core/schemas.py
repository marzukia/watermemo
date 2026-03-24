from datetime import datetime

from ninja import Schema


# --- Memory ---


class MemoryIn(Schema):
    content: str


class MemoryOut(Schema):
    id: int
    content: str
    created_datetime: datetime
    updated_datetime: datetime


class MemoryUpdate(Schema):
    content: str | None = None


# --- Distillation ---


class DistillationIn(Schema):
    content: str
    memory_id: int


class DistillationOut(Schema):
    id: int
    content: str
    memory_id: int
    is_core: bool
    created_datetime: datetime
    updated_datetime: datetime


class DistillationUpdate(Schema):
    content: str | None = None


# --- Search ---


class SearchQuery(Schema):
    query: str
    limit: int = 10
    # Cosine distance threshold: 0 = identical, 2 = opposite — lower is more similar
    threshold: float = 0.5


class SearchResultOut(Schema):
    id: int
    content: str
    memory_id: int
    is_core: bool
    distance: float


# --- Classify ---


class ClassifyQuery(Schema):
    text: str


class ClassifyOut(Schema):
    intent: str  # "delete", "store", or "ignore"
    confidence: str  # "high" or "low"
    scope: str  # "all" or "specific"
    recall: bool  # true if retrieving past memories would help answer this message


# --- Recall ---


class RecallQuery(Schema):
    query: str
    limit: int = 5
    threshold: float = 0.5
    decay_half_life_days: float = 30.0
    """Exponential decay half-life in days. Older memories are penalised by
    multiplying their cosine distance by e^(ln(2)/half_life * age_days).
    Higher values = slower decay. Set to 0 to disable decay.
    """


class RecallMemoryContext(Schema):
    id: int
    content: str
    distillation: str
    is_core: bool
    distance: float


class RecallOut(Schema):
    answer: str | None
    memories_used: int
    context: list[RecallMemoryContext]
