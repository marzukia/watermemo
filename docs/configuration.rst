Configuration
=============

watermemo is configured via environment variables. Copy ``.env.example`` to
``.env`` and adjust as needed.

Environment variables
---------------------

.. list-table::
   :header-rows: 1

   * - Variable
     - Default
     - Description
   * - ``SECRET_KEY``
     - (required)
     - Django secret key
   * - ``DEBUG``
     - ``False``
     - Enable Django debug mode
   * - ``ALLOWED_HOSTS``
     - ``localhost,127.0.0.1``
     - Comma-separated list of allowed hosts
   * - ``DB_NAME``
     - ``watermemo``
     - PostgreSQL database name
   * - ``DB_USER``
     - ``watermemo``
     - PostgreSQL user
   * - ``DB_PASSWORD``
     - ``postgres``
     - PostgreSQL password
   * - ``DB_HOST``
     - ``localhost``
     - PostgreSQL host
   * - ``DB_PORT``
     - ``5432``
     - PostgreSQL port
   * - ``LLM_BASE_URL``
     - ``http://host.docker.internal:11434/v1``
     - Ollama / OpenAI-compatible base URL
   * - ``LLM_API_KEY``
     - ``ollama``
     - API key for the LLM provider
   * - ``LLM_MODEL``
     - ``qwen3.5:35b-a3b``
     - Model name for chat / distillation
   * - ``LLM_EMBEDDING_MODEL``
     - ``nomic-embed-text``
     - Model name for embeddings
   * - ``LLM_EMBED_BASE_URL``
     - (empty, falls back to ``LLM_BASE_URL``)
     - Separate base URL for embeddings
   * - ``LLM_EMBED_API_KEY``
     - (empty, falls back to ``LLM_API_KEY``)
     - Separate API key for embeddings
