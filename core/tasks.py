"""Background distillation via ThreadPoolExecutor.

Pool is capped at 2 workers to match OLLAMA_NUM_PARALLEL.
"""

import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("watermemo.tasks")

_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="watermemo-bg")


def _distill_memory_sync(memory_id: int) -> None:
    """Distill a single memory. Runs in a background thread."""
    from django.db import close_old_connections

    close_old_connections()
    try:
        from core.integration import chat, load_prompt
        from core.models import Distillation, Memory

        memory = Memory.objects.get(pk=memory_id)

        system_prompt = load_prompt("DISTILLATION")
        text = chat(memory.content, system_prompt=system_prompt)

        if not text or text.strip().lower() == "no_memory":
            logger.info("Memory %d → no_memory, skipping", memory_id)
            return

        # Evaluate core status
        core_prompt = load_prompt("CORE_EVAL")
        core_raw = (chat(memory.content, system_prompt=core_prompt) or "").strip().lower()
        is_core = core_raw.startswith("true")

        Distillation.objects.create(content=text, memory=memory, is_core=is_core)
        logger.info("Memory %d distilled (core=%s)", memory_id, is_core)

    except Exception:
        logger.exception("Failed to distill memory %d", memory_id)
    finally:
        close_old_connections()


def _redistill_memory_sync(memory_id: int) -> None:
    """Delete existing distillations and re-distill from scratch."""
    from django.db import close_old_connections

    close_old_connections()
    try:
        from core.models import Distillation, Memory

        if not Memory.objects.filter(pk=memory_id).exists():
            logger.warning("Memory %d gone, skipping redistill", memory_id)
            return

        deleted, _ = Distillation.objects.filter(memory_id=memory_id).delete()
        logger.info("Deleted %d old distillation(s) for memory %d", deleted, memory_id)

        _distill_memory_sync(memory_id)

    except Exception:
        logger.exception("Failed to redistill memory %d", memory_id)
    finally:
        close_old_connections()


def submit_distill(memory_id: int) -> None:
    _pool.submit(_distill_memory_sync, memory_id)


def submit_redistill(memory_id: int) -> None:
    _pool.submit(_redistill_memory_sync, memory_id)
