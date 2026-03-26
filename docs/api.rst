API reference
=============

All endpoints are served under ``/api/``. Interactive docs are available at
``/api/docs`` when the server is running.

Health
------

.. list-table::
   :header-rows: 1

   * - Method
     - Path
     - Description
   * - GET
     - ``/api/health``
     - Health check + version

Memories
--------

.. list-table::
   :header-rows: 1

   * - Method
     - Path
     - Description
   * - GET
     - ``/api/memories/``
     - List memories (optional ``?user_id=``)
   * - POST
     - ``/api/memories/``
     - Store memory (distillation runs async)
   * - GET
     - ``/api/memories/{id}``
     - Get single memory
   * - PATCH
     - ``/api/memories/{id}``
     - Update memory (auto re-distills on content change)
   * - DELETE
     - ``/api/memories/{id}``
     - Delete memory + its distillations
   * - DELETE
     - ``/api/memories/``
     - Delete all (optional ``?user_id=``)

Distillations
-------------

.. list-table::
   :header-rows: 1

   * - Method
     - Path
     - Description
   * - GET
     - ``/api/distillations/``
     - List all distillations
   * - POST
     - ``/api/distillations/``
     - Create distillation manually
   * - PATCH
     - ``/api/distillations/{id}``
     - Update a distillation
   * - DELETE
     - ``/api/distillations/{id}``
     - Delete distillation
   * - POST
     - ``/api/distillations/search``
     - Vector similarity search

Recall and classify
-------------------

.. list-table::
   :header-rows: 1

   * - Method
     - Path
     - Description
   * - POST
     - ``/api/classify``
     - Classify intent (delete / store / ignore)
   * - POST
     - ``/api/recall``
     - RAG recall (blocking)
   * - POST
     - ``/api/recall/stream``
     - RAG recall (streaming SSE)

User scoping
------------

All list, search, recall, and delete endpoints accept an optional ``user_id``
parameter. When provided, results are filtered to memories belonging to that
user. The Open WebUI filter passes ``__user__["id"]`` automatically.
