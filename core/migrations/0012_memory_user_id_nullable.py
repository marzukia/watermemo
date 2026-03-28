from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_memory_user_id"),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE core_memory ALTER COLUMN user_id SET DEFAULT ''",
            reverse_sql="ALTER TABLE core_memory ALTER COLUMN user_id DROP DEFAULT",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE core_memory ALTER COLUMN user_id DROP NOT NULL",
            reverse_sql="ALTER TABLE core_memory ALTER COLUMN user_id SET NOT NULL",
        ),
    ]
