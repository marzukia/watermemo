"""GIN indexes and search-vector trigger for EventMemory (legacy)."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        # GIN indexes for fast full-text search
        migrations.RunSQL(
            sql="""
                CREATE INDEX IF NOT EXISTS idx_eventmemory_distillation_sv
                    ON core_eventmemory USING GIN (distillation_sv);
                CREATE INDEX IF NOT EXISTS idx_eventmemory_full_content_sv
                    ON core_eventmemory USING GIN (full_content_sv);
            """,
            reverse_sql="""
                DROP INDEX IF EXISTS idx_eventmemory_distillation_sv;
                DROP INDEX IF EXISTS idx_eventmemory_full_content_sv;
            """,
        ),
        # Trigger function: keep search vectors in sync automatically
        migrations.RunSQL(
            sql="""
                CREATE OR REPLACE FUNCTION core_eventmemory_sv_update()
                RETURNS TRIGGER LANGUAGE plpgsql AS $$
                BEGIN
                    IF TG_OP = 'INSERT'
                        OR NEW.distillation IS DISTINCT FROM OLD.distillation
                    THEN
                        NEW.distillation_sv :=
                            to_tsvector('english', COALESCE(NEW.distillation, ''));
                    END IF;

                    IF TG_OP = 'INSERT'
                        OR NEW.full_content IS DISTINCT FROM OLD.full_content
                    THEN
                        NEW.full_content_sv :=
                            to_tsvector('english', COALESCE(NEW.full_content, ''));
                    END IF;

                    RETURN NEW;
                END;
                $$;
            """,
            reverse_sql="DROP FUNCTION IF EXISTS core_eventmemory_sv_update;",
        ),
        migrations.RunSQL(
            sql="""
                CREATE TRIGGER core_eventmemory_sv_trigger
                BEFORE INSERT OR UPDATE OF distillation, full_content
                ON core_eventmemory
                FOR EACH ROW EXECUTE FUNCTION core_eventmemory_sv_update();
            """,
            reverse_sql="""
                DROP TRIGGER IF EXISTS core_eventmemory_sv_trigger
                    ON core_eventmemory;
            """,
        ),
    ]
