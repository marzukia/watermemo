Deployment
==========

This page shows how to deploy watermemo alongside Open WebUI, Ollama, and
supporting services using Docker Compose. The example below is a
production-ready reference stack.

Prerequisites
-------------

- Docker Engine 24+ with Compose V2
- NVIDIA Container Toolkit (if using GPU-accelerated Ollama)
- A PostgreSQL image built with **pgvector** (see ``build/postgres.Dockerfile``)

Minimal setup
-------------

If you only need watermemo and PostgreSQL:

.. code-block:: yaml

   services:
     postgres:
       build:
         context: .
         dockerfile: build/postgres.Dockerfile
       environment:
         POSTGRES_USER: watermemo
         POSTGRES_PASSWORD: "${DB_PASSWORD}"
         POSTGRES_DB: watermemo
       ports:
         - "5432:5432"
       volumes:
         - postgres:/var/lib/postgresql/data
       healthcheck:
         test: ["CMD-SHELL", "pg_isready -U watermemo"]
         interval: 5s
         timeout: 5s
         retries: 10

     watermemo:
       image: ghcr.io/marzukia/watermemo:latest
       restart: unless-stopped
       depends_on:
         postgres:
           condition: service_healthy
       environment:
         SECRET_KEY: "${SECRET_KEY}"
         DEBUG: "False"
         ALLOWED_HOSTS: "*"
         DB_NAME: watermemo
         DB_USER: watermemo
         DB_PASSWORD: "${DB_PASSWORD}"
         DB_HOST: postgres
         DB_PORT: "5432"
         LLM_BASE_URL: "http://ollama:11434/v1"
         LLM_API_KEY: "ollama"
         LLM_MODEL: "qwen3.5:35b-a3b-48k"
         LLM_EMBEDDING_MODEL: "nomic-embed-text"
       ports:
         - "8000:8000"
       healthcheck:
         test: ["CMD", "curl", "-fsS", "http://localhost:8000/api/health"]
         interval: 10s
         timeout: 5s
         retries: 10
       command:
         - sh
         - -c
         - >-
           uv run python manage.py migrate --noinput &&
           uv run gunicorn watermemo.asgi:application
           -k uvicorn.workers.UvicornWorker
           --bind 0.0.0.0:8000 --workers 2 --timeout 120

   volumes:
     postgres:

Full stack example
------------------

A complete stack with Open WebUI, Ollama (dual-GPU), model preloading,
SearXNG web search, Jupyter code execution, and a reverse proxy.
Sensitive values are read from environment variables — create a ``.env``
file alongside your ``docker-compose.yml``:

.. code-block:: bash

   # .env
   SECRET_KEY=change-me
   DB_PASSWORD=change-me
   WEBUI_SECRET_KEY=change-me
   JUPYTER_TOKEN=change-me

.. code-block:: yaml

   networks:
     internal_net:
       driver: bridge

   services:
     # ── Reverse proxy ──────────────────────────────────────────────
     npm:
       image: docker.io/jc21/nginx-proxy-manager:latest
       restart: unless-stopped
       ports:
         - "80:80"
         - "81:81"
         - "443:443"
       volumes:
         - ./app/data:/data
         - ./app/letsencrypt:/etc/letsencrypt
       networks:
         - internal_net

     # ── Open WebUI ─────────────────────────────────────────────────
     open-webui:
       image: ghcr.io/open-webui/open-webui:main
       ports:
         - "3000:8080"
       extra_hosts:
         - "host.docker.internal:host-gateway"
       environment:
         OLLAMA_BASE_URL: "http://ollama:11434"
         LOG_LEVEL: "INFO"
         WEBUI_SECRET_KEY: "${WEBUI_SECRET_KEY}"
         USER_AGENT: "open-webui-local/1.0"
         DATABASE_URL: "postgresql://webui:${DB_PASSWORD}@postgres:5432/webui"
         FORWARDED_ALLOW_IPS: "*"
         TRUSTED_PROXIES: "*"
         # Jupyter code execution (optional)
         CODE_EXECUTION_ENGINE: "jupyter"
         CODE_EXECUTION_JUPYTER_URL: "http://jupyter:8888"
         CODE_EXECUTION_JUPYTER_AUTH: "${JUPYTER_TOKEN}"
       volumes:
         - openwebui:/app/backend/data
       restart: unless-stopped
       healthcheck:
         test: ["CMD", "sh", "-lc", "curl -fsS http://localhost:8080/ >/dev/null || exit 1"]
         interval: 5s
         timeout: 3s
         retries: 30
       networks:
         - internal_net

     # ── Ollama (GPU) ───────────────────────────────────────────────
     ollama:
       image: ollama/ollama:latest
       volumes:
         - ollama:/root/.ollama
       restart: unless-stopped
       ports:
         - "11434:11434"
       networks:
         - internal_net
       dns:
         - 1.1.1.1
         - 8.8.8.8
       runtime: nvidia
       environment:
         OLLAMA_KEEP_ALIVE: "-1"
         OLLAMA_FLASH_ATTENTION: "1"
         OLLAMA_NUM_PARALLEL: "2"
         OLLAMA_MAX_LOADED_MODELS: "2"
         OLLAMA_SCHED_SPREAD: "1"
         NVIDIA_VISIBLE_DEVICES: all
         CUDA_VISIBLE_DEVICES: "0,1"
         NVIDIA_DRIVER_CAPABILITIES: compute,utility
       deploy:
         resources:
           reservations:
             devices:
               - driver: nvidia
                 count: all
                 capabilities: [gpu]
       healthcheck:
         test: ["CMD", "sh", "-lc", "ollama list >/dev/null 2>&1 || curl -fsS http://127.0.0.1:11434/api/tags >/dev/null"]
         interval: 10s
         timeout: 5s
         retries: 30

     # ── Model preloader (runs once) ────────────────────────────────
     ollama-preload:
       image: curlimages/curl:latest
       depends_on:
         ollama:
           condition: service_healthy
       restart: "no"
       networks:
         - internal_net
       entrypoint: ["/bin/sh", "-c"]
       command:
         - |
           echo "Pulling models..."
           curl -sf http://ollama:11434/api/pull -d '{"name":"qwen3.5:35b-a3b"}'
           curl -sf http://ollama:11434/api/pull -d '{"name":"nomic-embed-text"}'
           echo "Creating custom model variant..."
           curl -sf http://ollama:11434/api/create -d '{
             "name":"qwen3.5:35b-a3b-48k",
             "from":"qwen3.5:35b-a3b",
             "parameters":{
               "num_ctx":49152,
               "temperature":0.7,
               "top_p":0.8,
               "top_k":20,
               "min_p":0.0,
               "repeat_penalty":1.2,
               "num_predict":32768,
               "think":false
             }
           }'
           echo "Pinning models in memory..."
           curl -sf http://ollama:11434/api/generate \
             -d '{"model":"qwen3.5:35b-a3b-48k","prompt":"","keep_alive":-1}'
           curl -sf http://ollama:11434/api/embeddings \
             -d '{"model":"nomic-embed-text","prompt":"warmup","keep_alive":-1}'
           echo "Done."

     # ── Jupyter (code execution backend) ───────────────────────────
     jupyter:
       image: jupyter/minimal-notebook:latest
       restart: unless-stopped
       environment:
         JUPYTER_TOKEN: "${JUPYTER_TOKEN}"
       volumes:
         - ./jupyter-data:/home/jovyan/work
       networks:
         - internal_net

     # ── SearXNG (web search) ───────────────────────────────────────
     searxng:
       image: searxng/searxng:latest
       ports:
         - "8080:8080"
       environment:
         BASE_URL: "http://localhost:8080/"
         INSTANCE_NAME: "Local SearXNG"
       volumes:
         - ./searxng-config:/etc/searxng
       restart: unless-stopped
       healthcheck:
         test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/').read()"]
         interval: 10s
         timeout: 5s
         retries: 30
       networks:
         - internal_net

     # ── PostgreSQL (pgvector) ──────────────────────────────────────
     postgres:
       build:
         context: .
         dockerfile: build/postgres.Dockerfile
       environment:
         POSTGRES_USER: postgres
         POSTGRES_PASSWORD: "${DB_PASSWORD}"
         POSTGRES_DB: postgres
       ports:
         - "5432:5432"
       volumes:
         - postgres:/var/lib/postgresql/data
       healthcheck:
         test: ["CMD-SHELL", "pg_isready -U postgres"]
         interval: 5s
         timeout: 5s
         retries: 10
       networks:
         - internal_net

     # ── watermemo ──────────────────────────────────────────────────
     watermemo:
       image: ghcr.io/marzukia/watermemo:latest
       restart: unless-stopped
       depends_on:
         postgres:
           condition: service_healthy
       environment:
         SECRET_KEY: "${SECRET_KEY}"
         DEBUG: "False"
         ALLOWED_HOSTS: "*"
         DB_NAME: watermemo
         DB_USER: postgres
         DB_PASSWORD: "${DB_PASSWORD}"
         DB_HOST: postgres
         DB_PORT: "5432"
         LLM_BASE_URL: "http://ollama:11434/v1"
         LLM_API_KEY: "ollama"
         LLM_MODEL: "qwen3.5:35b-a3b-48k"
         LLM_EMBEDDING_MODEL: "nomic-embed-text"
       ports:
         - "8000:8000"
       healthcheck:
         test: ["CMD", "curl", "-fsS", "http://localhost:8000/api/health"]
         interval: 10s
         timeout: 5s
         retries: 10
       command:
         - sh
         - -c
         - >-
           uv run python manage.py migrate --noinput &&
           uv run gunicorn watermemo.asgi:application
           -k uvicorn.workers.UvicornWorker
           --bind 0.0.0.0:8000 --workers 2 --timeout 120
       networks:
         - internal_net

   volumes:
     openwebui:
     ollama:
     postgres:

Notes
-----

- The ``ollama-preload`` service pulls models and creates a custom variant
  with a 48k context window and non-thinking mode. Adjust the model name and
  parameters to suit your hardware.
- Remove the ``runtime: nvidia`` and ``deploy.resources`` sections from
  ``ollama`` if you do not have NVIDIA GPUs.
- The ``postgres`` image is built from ``build/postgres.Dockerfile`` which
  installs pgvector on top of the official PostgreSQL 17 image.
- Open WebUI's ``CODE_EXECUTION_*`` variables enable Jupyter-backed code
  execution. Remove the ``jupyter`` service and those variables if not needed.
- watermemo runs migrations automatically on startup via its ``command``.
  On first boot, create the ``watermemo`` database if your PostgreSQL instance
  uses a different default:

  .. code-block:: bash

     docker exec -it postgres psql -U postgres -c "CREATE DATABASE watermemo;"
