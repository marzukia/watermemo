Open WebUI filter
=================

The filter provides fully automatic recall and storage on every exchange.

Setup
-----

1. Go to **Workspace → Functions → + New Function**, set type to **Filter**.
2. Paste the contents of ``open_webui/filter.py``.
3. Set the ``base_url`` valve to your watermemo instance
   (e.g. ``http://host.docker.internal:8000/api``).
4. Enable the filter on your model.

Valves
------

.. list-table::
   :header-rows: 1

   * - Valve
     - Default
     - Description
   * - ``base_url``
     - ``http://web:8000/api``
     - watermemo API root
   * - ``recall_limit``
     - ``5``
     - Max memories injected per prompt
   * - ``recall_threshold``
     - ``0.7``
     - Cosine distance cut-off for recall
   * - ``update_threshold``
     - ``0.15``
     - Distance below which an existing memory is updated instead of creating new
   * - ``store_exchanges``
     - ``true``
     - Store user+assistant turn after each reply
   * - ``context_messages``
     - ``6``
     - Recent messages used to build recall query
   * - ``enabled``
     - ``true``
     - Master on/off switch

Behaviour
---------

**Inlet** (before LLM)
   Embeds recent conversation context, searches distillations, and injects
   matching memories into the system prompt.

**Outlet** (after LLM)
   Stores the exchange as a new memory (or updates an existing near-duplicate).
   Keyword-based delete detection handles "forget" / "delete memory" requests
   without an LLM call.
