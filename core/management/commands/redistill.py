"""Re-distill all memories with the current prompt."""

from django.core.management.base import BaseCommand

from core.integration import chat, load_prompt, embed
from core.models import Distillation, Memory


class Command(BaseCommand):
    help = "Re-distill all existing memories with the current prompt."

    def handle(self, *args, **options):
        system_prompt = load_prompt("DISTILLATION")
        core_prompt = load_prompt("CORE_EVAL")

        memories = Memory.objects.all()
        total = memories.count()
        self.stdout.write(f"Re-distilling {total} memories...")

        for i, memory in enumerate(memories, 1):
            self.stdout.write(f"  [{i}/{total}] Memory #{memory.id}...")

            # Generate new distillation text
            new_text = chat(memory.content, system_prompt=system_prompt)
            if not new_text or new_text.strip() == "no_memory":
                self.stdout.write(f"    → skipped (no_memory)")
                continue

            # Re-evaluate core status
            core_raw = (chat(memory.content, system_prompt=core_prompt) or "").strip().lower()
            is_core = core_raw.startswith("true")

            # Update or create distillation
            dist = Distillation.objects.filter(memory=memory).first()
            if dist:
                dist.content = new_text
                dist.is_core = is_core
                dist.save(update_fields=["content", "is_core"])
            else:
                dist = Distillation.objects.create(
                    content=new_text, memory=memory, is_core=is_core
                )

            # Re-generate embedding
            try:
                dist.embedding = embed(dist.content)
                dist.save(update_fields=["embedding"])
            except Exception as e:
                self.stdout.write(f"    → embedding failed: {e}")

            self.stdout.write(f"    → done (core={is_core})")

        self.stdout.write(self.style.SUCCESS("All memories re-distilled."))
