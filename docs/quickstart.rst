Quick start
===========

Requirements
------------

- Python 3.14+
- PostgreSQL 14+ with `pgvector <https://github.com/pgvector/pgvector>`_
- An LLM accessible via Ollama or any OpenAI-compatible API
- An embedding model (default: ``nomic-embed-text`` via Ollama)

Installation
------------

.. code-block:: bash

   git clone https://github.com/marzukia/watermemo.git
   cd watermemo
   cp .env.example .env    # edit LLM_MODEL, DB_* etc.

   # Install dependencies
   uv sync

   # Run migrations
   uv run python manage.py migrate

   # Start the server
   uv run python manage.py runserver 0.0.0.0:8000

API docs are available at ``http://localhost:8000/api/docs``.

Docker
------

.. code-block:: bash

   # Start PostgreSQL (pgvector) + watermemo
   docker compose up --build -d

   # Migrations run automatically on container start

The web container reaches Ollama via ``host.docker.internal:11434`` by default.
Override with ``LLM_BASE_URL`` in your ``.env``.

Testing
-------

.. code-block:: bash

   uv sync --dev
   uv run pytest
