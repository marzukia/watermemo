# watermemo

A memory layer for LLMs. Stores raw conversation exchanges, auto-generates semantic distillations via an LLM, and retrieves relevant memories using pgvector similarity search with temporal decay.

Designed for use with [Open WebUI](https://github.com/open-webui/open-webui) via a filter plugin, but works as a standalone REST API with any client.

## How it works

```
User + Assistant exchange
        │
        ▼
  POST /api/memories/         ← stores raw content (returns immediately)
        │
        ├──▶ Background thread: LLM distillation (DISTILLATION.md prompt)
        │         │
        │         ├──▶ Evaluate core status (CORE_EVAL.md prompt)
        │         └──▶ Create Distillation record (embedding auto-generated)
        │
        ▼
  POST /api/distillations/search   ← embed query → cosine similarity search
        │
        ▼
  Recalled distillations injected into system prompt
```

**Memory** - raw `User: ... \n Assistant: ...` exchange text.

**Distillation** - LLM-generated summary (1-4 factual sentences, third person). Each has a 768-dim embedding from nomic-embed-text and a PostgreSQL full-text search vector.

**Core memories** - identity-level facts (name, location, occupation) that get a 2x looser recall threshold so they're always surfaced.

## Architecture

```
watermemo/            ← Django project (settings, urls, wsgi/asgi)
core/
  models.py           ← Memory, Distillation (pgvector + FTS)
  api.py              ← REST endpoints (Django Ninja)
  schemas.py          ← Pydantic request/response schemas
  signals.py          ← post_save: auto-populate search vector + embedding
  tasks.py            ← Background ThreadPoolExecutor for async distillation
  integration.py      ← LLM client (Ollama native API + OpenAI embeddings)
  prompts/            ← System prompt templates
    DISTILLATION.md   ← Summarise exchange → factual sentences
    CORE_EVAL.md      ← Is this a core identity fact? → true/false
    RECALL.md         ← Answer from retrieved memories
    CLASSIFY.md       ← Classify intent (delete/store/ignore)
  management/commands/
    redistill.py      ← Re-distill all memories with current prompt
    consolidate.py    ← Merge near-duplicate memories
open_webui/
  filter.py           ← Open WebUI filter (inlet: recall, outlet: store)
```

## Requirements

- Python 3.14+
- PostgreSQL 14+ with [pgvector](https://github.com/pgvector/pgvector)
- An LLM accessible via Ollama or any OpenAI-compatible API
- An embedding model (default: `nomic-embed-text` via Ollama)

## Quick start

```bash
# 1. Clone and configure
git clone https://github.com/marzukia/watermemo.git
cd watermemo
cp .env.example .env    # edit LLM_MODEL, DB_* etc.

# 2. Install dependencies
uv sync

# 3. Run migrations
uv run python manage.py migrate

# 4. Start the server
uv run python manage.py runserver 0.0.0.0:8000
```

API docs: http://localhost:8000/api/docs

## Docker

```bash
# Start PostgreSQL (pgvector) + watermemo web service
docker compose up --build -d

# Migrations run automatically on container start
```

The web container reaches Ollama via `host.docker.internal:11434` by default.
Override with `LLM_BASE_URL` in your `.env`.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check + version |
| GET | `/api/memories/` | List memories (optional `?user_id=`) |
| POST | `/api/memories/` | Store memory (distillation runs async) |
| GET | `/api/memories/{id}` | Get single memory |
| PATCH | `/api/memories/{id}` | Update memory (auto re-distills if content changed) |
| DELETE | `/api/memories/{id}` | Delete memory + its distillations |
| DELETE | `/api/memories/` | Delete all (optional `?user_id=`) |
| GET | `/api/distillations/` | List all distillations |
| POST | `/api/distillations/` | Create distillation manually |
| PATCH | `/api/distillations/{id}` | Fix a faulty distillation |
| DELETE | `/api/distillations/{id}` | Delete distillation |
| POST | `/api/distillations/search` | Vector similarity search |
| POST | `/api/classify` | Classify intent (delete/store/ignore) |
| POST | `/api/recall` | RAG recall (blocking) |
| POST | `/api/recall/stream` | RAG recall (streaming SSE) |

### User scoping

All list, search, recall, and delete endpoints accept an optional `user_id` field. When provided, results are filtered to memories belonging to that user. The Open WebUI filter passes `__user__["id"]` automatically.

### Temporal decay

Recall penalises older memories using exponential decay:

$$\text{score} = \text{cosine\\_distance} \times e^{\frac{\ln 2}{\text{half\\_life}} \times \text{age\\_days}}$$

Control via `decay_half_life_days` in recall requests (default: 30). Set to 0 to disable.

## Management commands

```bash
# Re-distill all memories with the current DISTILLATION.md prompt
uv run python manage.py redistill

# Find and merge near-duplicate memories (dry-run first)
uv run python manage.py consolidate --dry-run --threshold 0.08

# Apply merges
uv run python manage.py consolidate --threshold 0.08
```

## Open WebUI integration

### Filter (recommended)

The filter provides fully automatic recall + storage on every exchange.

1. Go to **Workspace → Functions → + New Function**, set type to **Filter**
2. Paste the contents of [`open_webui/filter.py`](open_webui/filter.py)
3. Set the `base_url` valve to your watermemo instance (e.g. `http://host.docker.internal:8000/api`)
4. Enable the filter on your model

| Valve | Default | Description |
|-------|---------|-------------|
| `base_url` | `http://web:8000/api` | watermemo API root |
| `recall_limit` | `5` | Max memories injected per prompt |
| `recall_threshold` | `0.7` | Cosine distance cut-off for recall |
| `update_threshold` | `0.15` | Distance below which an existing memory is updated instead of creating new |
| `store_exchanges` | `true` | Store user+assistant turn after each reply |
| `context_messages` | `6` | Recent messages used to build recall query |
| `enabled` | `true` | Master on/off switch |

**Inlet** (before LLM): embeds recent conversation context → searches distillations → injects matching memories into system prompt.

**Outlet** (after LLM): stores the exchange as a new memory (or updates an existing near-duplicate). Keyword-based delete detection handles "forget" / "delete memory" requests without an LLM call.

## Fixing faulty memories

```bash
# Fix a distillation directly
curl -X PATCH http://localhost:8000/api/distillations/{id} \
  -H "Content-Type: application/json" \
  -d '{"content": "Corrected summary here"}'

# Update raw memory content (triggers automatic re-distillation)
curl -X PATCH http://localhost:8000/api/memories/{id} \
  -H "Content-Type: application/json" \
  -d '{"content": "Corrected full content here"}'
```

## Testing

```bash
uv sync --dev
uv run pytest
```

## License

MIT
