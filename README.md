# memorai

A memory layer for LLMs. Stores raw content, auto-generates semantic distillations via an LLM, and retrieves relevant memories using vector similarity with temporal decay.

## Architecture

```
memorai/          ← Django project package (settings, urls, wsgi, asgi)
core/             ← main app
  models.py       ← Memory, Distillation (pgvector embeddings + FTS)
  api.py          ← REST endpoints (Django Ninja)
  schemas.py      ← Pydantic request/response schemas
  signals.py      ← post_save: auto-populates sv + embedding fields
  integration.py  ← LLM client (chat, stream_chat, embed)
  prompts/        ← System prompt files (DISTILLATION.md, RECALL.md)
  migrations/     ← Database migrations
manage.py
Dockerfile
docker-compose.yml
```

**Memory flow:**

1. `POST /api/memories/` stores raw content as a `Memory`
2. A `Distillation` is auto-generated via LLM using `DISTILLATION.md` prompt
3. Both records get a `SearchVectorField` (FTS) and a 768-dim `VectorField` (nomic-embed-text)

**Recall flow:**

1. Query is embedded with nomic-embed-text
2. Closest `Distillation` records found by cosine distance
3. Temporal decay applied: older memories are penalised exponentially
4. Full `Memory` content resolved via FK
5. LLM answers using retrieved context (`RECALL.md` prompt)

## Requirements

- Python 3.14+
- PostgreSQL 14+ with [pgvector](https://github.com/pgvector/pgvector) extension
- [Ollama](https://ollama.com) running locally (or any OpenAI-compatible endpoint)
- Models: `gemma3:latest` (chat), `nomic-embed-text` (embeddings)

## Setup

```bash
# 1. Copy and configure env
cp .env.example .env

# 2. Install dependencies
uv sync

# 3. Run migrations
uv run python manage.py migrate

# 4. (Optional) Create admin superuser
uv run python manage.py createsuperuser

# 5. Run dev server
uv run python manage.py runserver
```

API docs available at: http://localhost:8000/api/docs
Debug UI available at: http://localhost:8000

## Docker

```bash
# Start Postgres (pgvector) + web service
docker compose up --build

# Migrations run automatically on container start
```

> The web container reaches Ollama via `host.docker.internal:11434` by default.
> Override with `LLM_BASE_URL` in your `.env`.

## API Endpoints

| Method | Path                        | Description                          |
| ------ | --------------------------- | ------------------------------------ |
| GET    | `/api/health`               | Health check + version               |
| GET    | `/api/memories/`            | List all memories                    |
| POST   | `/api/memories/`            | Store memory (auto-distills via LLM) |
| GET    | `/api/memories/{id}`        | Get memory                           |
| PATCH  | `/api/memories/{id}`        | Update memory content                |
| DELETE | `/api/memories/{id}`        | Delete memory                        |
| GET    | `/api/distillations/`       | List all distillations               |
| POST   | `/api/distillations/`       | Create distillation manually         |
| GET    | `/api/distillations/{id}`   | Get distillation                     |
| PATCH  | `/api/distillations/{id}`   | Correct a faulty distillation        |
| DELETE | `/api/distillations/{id}`   | Delete distillation                  |
| POST   | `/api/distillations/search` | Vector search over distillations     |
| POST   | `/api/recall`               | RAG recall (blocking)                |
| POST   | `/api/recall/stream`        | RAG recall (streaming SSE)           |

## Fixing Faulty Memories

If a distillation is wrong or misleading, patch it directly:

```bash
curl -X PATCH http://localhost:8000/api/distillations/{id} \
  -H "Content-Type: application/json" \
  -d '{"content": "Corrected summary here"}'
```

To update the raw memory content (which will re-trigger embedding + FTS):

```bash
curl -X PATCH http://localhost:8000/api/memories/{id} \
  -H "Content-Type: application/json" \
  -d '{"content": "Corrected full content here"}'
```

## Temporal Decay

Recall penalises older memories using exponential decay:

$$\text{score} = \text{cosine\_distance} \times e^{\frac{\ln 2}{\text{half\_life}} \times \text{age\_days}}$$

Control via `decay_half_life_days` in recall requests (default: `30`):

```json
{
  "query": "what happened with the deployment?",
  "decay_half_life_days": 7
}
```

Set to `0` to disable decay entirely. Relevance always dominates — decay only
breaks ties between equally relevant memories of different ages.

## Open WebUI Integration

Add this as a **Tool** in Open WebUI (**Workspace → Tools → + New Tool**):

```python
import requests

class Tools:
    def __init__(self):
        self.base_url = "http://your-memorai-host:8000/api"
        self.headers = {"Authorization": "Bearer your-secret-token"}

    def store_memory(self, content: str) -> str:
        """
        Store something in long-term memory for later recall.
        Use this when the user says to remember something, or when
        important information should be retained across conversations.
        :param content: The full content to store as a memory.
        """
        res = requests.post(
            f"{self.base_url}/memories/",
            json={"content": content},
            headers=self.headers,
        )
        data = res.json()
        return f"Stored as Memory #{data['id']}."

    def recall_memories(self, query: str) -> str:
        """
        Search long-term memory for information relevant to a query.
        Use this when the user asks about something that may have been
        discussed or stored previously.
        :param query: The question or topic to search memory for.
        """
        res = requests.post(
            f"{self.base_url}/recall",
            json={"query": query, "limit": 5, "threshold": 0.6},
            headers=self.headers,
        )
        data = res.json()
        if not data.get("memories_used"):
            return "No relevant memories found."
        parts = [f"[Memory #{c['id']}] {c['distillation']}" for c in data["context"]]
        return "\n".join(parts)
```

Enable the tool on your chosen model. The LLM will automatically call
`store_memory` or `recall_memories` based on the conversation context.

### Auto-recall + Auto-store (Filter)

For fully automatic behaviour — recall injected into every prompt, exchange
stored after every response — use a **Filter** instead of (or alongside) the
Tool above.

Go to **Workspace → Functions → + New Function**, set type to **Filter**, and
paste the contents of [`open_webui/filter.py`](open_webui/filter.py).

Configure the valve `base_url` to point at your memorai instance
(`http://web:8000/api` if both run in the same Docker network).

| Valve              | Default               | Description                                |
| ------------------ | --------------------- | ------------------------------------------ |
| `base_url`         | `http://web:8000/api` | memorai API root                           |
| `recall_limit`     | `5`                   | Max memories injected per prompt           |
| `recall_threshold` | `0.5`                 | Cosine distance cut-off                    |
| `store_exchanges`  | `true`                | Store user+assistant turn after each reply |
| `enabled`          | `true`                | Master on/off switch                       |

> **How it works:** The `inlet` hook fires before the LLM sees the user's
> message — it calls `/api/recall` and prepends the relevant distillations to
> the system prompt. The `outlet` hook fires after the LLM responds — it
> calls `/api/memories/` to store the full exchange for future recall.

## Features

- Django Ninja REST API with auto-generated OpenAPI docs
- PostgreSQL via Django ORM
- Config via `.env` using `python-decouple`
- `core` app with `EventMemory` model, schemas, and CRUD endpoints
- Django admin registered

## Structure

```
memorai/          ← Django project package (settings, urls, wsgi, asgi)
core/             ← main app (models, schemas, api, admin, migrations)
manage.py
```

## Setup

```bash
# 1. Copy env config
cp .env.example .env

# 2. Install dependencies
uv sync

# 3. Create and run migrations
uv run python manage.py makemigrations
uv run python manage.py migrate

# 4. (Optional) Create a superuser for admin
uv run python manage.py createsuperuser

# 5. Run the dev server
uv run python manage.py runserver
```

## Endpoints

| Method | Path                       | Description  |
| ------ | -------------------------- | ------------ |
| GET    | `/api/health`              | Health check |
| GET    | `/api/event-memories/`     | List all     |
| POST   | `/api/event-memories/`     | Create       |
| GET    | `/api/event-memories/{id}` | Get one      |
| DELETE | `/api/event-memories/{id}` | Delete       |

Interactive API docs: http://localhost:8000/api/docs

## Features

- FastAPI HTTP API
- PostgreSQL connection via SQLAlchemy
- Config management via Pydantic settings (`.env`)
- Alembic migrations
- Basic `EventMemory` table with create/list endpoints

## Setup

1. Copy environment config:

   cp .env.example .env

2. Install dependencies:

   uv sync

3. Run migrations:

   uv run alembic upgrade head

4. Run the API:

   uv run uvicorn main:app --reload

## Migration commands

- Create a migration from model changes:

  uv run alembic revision --autogenerate -m "describe_change"

- Apply migrations:

  uv run alembic upgrade head

- Roll back one migration:

  uv run alembic downgrade -1

## Endpoints

- `GET /health`
- `POST /event-memories`
- `GET /event-memories`

## Example request body

```json
{
  "title": "My first event",
  "content": "Remember to check in with the team"
}
```
