from datetime import datetime
from typing import Annotated

from ninja import Schema
from pydantic import Field

# Maximum length for user-supplied text content (64 KiB of UTF-8 characters).
MAX_CONTENT_LEN = 65_536
# Maximum length for user_id values.
MAX_USER_ID_LEN = 255

_Content = Annotated[str, Field(max_length=MAX_CONTENT_LEN)]
_UserId = Annotated[str, Field(max_length=MAX_USER_ID_LEN)]
_Query = Annotated[str, Field(max_length=MAX_CONTENT_LEN)]


# Memory


class MemoryIn(Schema):
    content: _Content
    user_id: _UserId = ""


class MemoryOut(Schema):
    id: int
    content: str
    user_id: str
    created_datetime: datetime
    updated_datetime: datetime


class MemoryUpdate(Schema):
    content: _Content | None = None


# Distillation


class DistillationIn(Schema):
    content: _Content
    memory_id: int


class DistillationOut(Schema):
    id: int
    content: str
    memory_id: int
    is_core: bool
    created_datetime: datetime
    updated_datetime: datetime


class DistillationUpdate(Schema):
    content: _Content | None = None


# Search


class SearchQuery(Schema):
    query: _Query
    limit: int = 10
    threshold: float = 0.5  # cosine distance: 0 = identical, 2 = opposite
    user_id: _UserId = ""


class SearchResultOut(Schema):
    id: int
    content: str
    memory_id: int
    is_core: bool
    distance: float


# Classify


class ClassifyQuery(Schema):
    text: _Query


class ClassifyOut(Schema):
    intent: str  # delete | store | ignore
    confidence: str  # high | low
    scope: str  # all | specific
    recall: bool  # whether recall would help answer


# Recall


class RecallQuery(Schema):
    query: _Query
    limit: int = 5
    threshold: float = 0.5
    decay_half_life_days: float = 30.0
    user_id: _UserId = ""
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
