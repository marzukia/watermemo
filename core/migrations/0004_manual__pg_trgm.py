"""
Manual migration: pg_trgm extension and trigram indexes on distillation.

pg_trgm breaks text into trigrams (3-char windows) enabling fuzzy/partial
matching without an external model. Combined with FTS it handles typos,
partial words, and queries that share no exact stems with the stored text.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_remove_eventmemory_content"),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS pg_trgm;",
            reverse_sql="DROP EXTENSION IF EXISTS pg_trgm;",
        ),
        # GIN trigram index on distillation — used for similarity() queries
        migrations.RunSQL(
            sql="""
                CREATE INDEX IF NOT EXISTS idx_eventmemory_distillation_trgm
                    ON core_eventmemory
                    USING GIN (distillation gin_trgm_ops);
            """,
            reverse_sql="""
                DROP INDEX IF EXISTS idx_eventmemory_distillation_trgm;
            """,
        ),
    ]
