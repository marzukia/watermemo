from datetime import datetime

from ninja import Schema


# Memory


class MemoryIn(Schema):
    content: str
    user_id: str = ""


class MemoryOut(Schema):
    id: int
    content: str
    user_id: str
    created_datetime: datetime
    updated_datetime: datetime


class MemoryUpdate(Schema):
    content: str | None = None


# Distillation


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


# Search


class SearchQuery(Schema):
    query: str
    limit: int = 10
    threshold: float = 0.5  # cosine distance: 0 = identical, 2 = opposite
    user_id: str = ""


class SearchResultOut(Schema):
    id: int
    content: str
    memory_id: int
    is_core: bool
    distance: float


# Classify


class ClassifyQuery(Schema):
    text: str


class ClassifyOut(Schema):
    intent: str  # delete | store | ignore
    confidence: str  # high | low
    scope: str  # all | specific
    recall: bool  # whether recall would help answer


# Recall


class RecallQuery(Schema):
    query: str
    limit: int = 5
    threshold: float = 0.5
    decay_half_life_days: float = 30.0
    user_id: str = ""
    """Half-life in days for exponential age decay on cosine distance.
    Set to 0 to disable."""


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
