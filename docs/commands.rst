Management commands
===================

redistill
---------

Re-distill all memories using the current ``DISTILLATION.md`` prompt. Useful
after updating the prompt to regenerate all distillations.

.. code-block:: bash

   uv run python manage.py redistill

consolidate
-----------

Find and merge near-duplicate memories based on cosine similarity.

.. code-block:: bash

   # Preview what would be merged
   uv run python manage.py consolidate --dry-run --threshold 0.08

   # Apply merges
   uv run python manage.py consolidate --threshold 0.08

Options:

``--threshold``
   Cosine distance below which two memories are considered duplicates
   (default: ``0.08``).

``--dry-run``
   Show what would be merged without making changes.
