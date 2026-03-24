"""Merge memories with near-duplicate distillations."""

from django.core.management.base import BaseCommand, CommandParser
from django.db import connection


class Command(BaseCommand):
    help = "Find and merge memories with very similar distillations."

    def add_arguments(self, parser: CommandParser):
        parser.add_argument(
            "--threshold",
            type=float,
            default=0.08,
            help="Cosine distance below which two distillations are considered duplicates (default: 0.08)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be merged without making changes",
        )
        parser.add_argument(
            "--user-id",
            type=str,
            default="",
            help="Only consolidate memories for a specific user",
        )

    def handle(self, *args, **options):
        from core.models import Distillation, Memory
        from core.tasks import submit_redistill

        threshold = options["threshold"]
        dry_run = options["dry_run"]
        user_id = options["user_id"]

        # Pairwise cosine distance via pgvector <=>
        user_clause = ""
        params: list = [threshold]
        if user_id:
            user_clause = "AND m1.user_id = %s AND m2.user_id = %s"
            params.extend([user_id, user_id])

        sql = f"""
            SELECT a.id AS a_id, b.id AS b_id,
                   a.memory_id AS a_mem, b.memory_id AS b_mem,
                   a.content AS a_content, b.content AS b_content,
                   (a.embedding <=> b.embedding) AS distance
            FROM core_distillation a
            JOIN core_memory m1 ON a.memory_id = m1.id
            CROSS JOIN core_distillation b
            JOIN core_memory m2 ON b.memory_id = m2.id
            WHERE a.id < b.id
              AND a.embedding IS NOT NULL
              AND b.embedding IS NOT NULL
              AND a.memory_id != b.memory_id
              AND (a.embedding <=> b.embedding) < %s
              {user_clause}
            ORDER BY distance
        """

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            pairs = cursor.fetchall()

        if not pairs:
            self.stdout.write(self.style.SUCCESS("No duplicates found."))
            return

        self.stdout.write(f"Found {len(pairs)} near-duplicate pair(s):\n")

        # Greedy merge: skip memories already involved in a merge
        merged_memory_ids: set[int] = set()
        merge_count = 0

        for _a_id, _b_id, a_mem, b_mem, a_content, b_content, distance in pairs:
            if a_mem in merged_memory_ids or b_mem in merged_memory_ids:
                continue

            self.stdout.write(
                f"  distance={distance:.4f}  memory #{a_mem} ↔ #{b_mem}\n"
                f"    A: {a_content[:80]}...\n"
                f"    B: {b_content[:80]}...\n"
            )

            if dry_run:
                merge_count += 1
                merged_memory_ids.add(b_mem)
                continue

            # Keep A (older ID = created first), merge B's raw content into A
            try:
                keep = Memory.objects.get(pk=a_mem)
                remove = Memory.objects.get(pk=b_mem)
            except Memory.DoesNotExist:
                continue

            keep.content = keep.content + "\n---\n" + remove.content
            keep.save(update_fields=["content"])

            remove.delete()
            merged_memory_ids.add(b_mem)

            submit_redistill(keep.id)
            merge_count += 1
            self.stdout.write(f"    → Merged into memory #{keep.id}, re-distilling...\n")

        action = "Would merge" if dry_run else "Merged"
        self.stdout.write(
            self.style.SUCCESS(f"\n{action} {merge_count} duplicate pair(s).")
        )
