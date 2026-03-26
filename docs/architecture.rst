Architecture
============

Overview
--------

.. code-block:: text

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

Key concepts
------------

**Memory**
   Raw ``User: ... \n Assistant: ...`` exchange text.

**Distillation**
   LLM-generated summary (1-4 factual sentences, third person). Each distillation
   has a 768-dim embedding from ``nomic-embed-text`` and a PostgreSQL full-text
   search vector.

**Core memories**
   Identity-level facts (name, location, occupation) that get a 2× looser recall
   threshold so they're always surfaced.

Project layout
--------------

.. code-block:: text

   watermemo/            ← Django project (settings, urls, wsgi/asgi)
   core/
     models.py           ← Memory, Distillation (pgvector + FTS)
     api.py              ← REST endpoints (Django Ninja)
     schemas.py          ← Pydantic request/response schemas
     signals.py          ← post_save: auto-populate search vector + embedding
     tasks.py            ← Background ThreadPoolExecutor for async distillation
     integration.py      ← LLM client (Ollama native API + OpenAI embeddings)
     prompts/            ← System prompt templates
     management/commands/
       redistill.py      ← Re-distill all memories with current prompt
       consolidate.py    ← Merge near-duplicate memories
   open_webui/
     filter.py           ← Open WebUI filter (inlet: recall, outlet: store)

Temporal decay
--------------

Recall penalises older memories using exponential decay:

.. math::

   \text{score} = \text{cosine\_distance} \times e^{\frac{\ln 2}{\text{half\_life}} \times \text{age\_days}}

Control via ``decay_half_life_days`` in recall requests (default: 30). Set to 0
to disable.
