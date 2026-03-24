import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0005_distillation_memory_alter_eventmemory_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="distillation",
            name="memory",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="distillations",
                to="core.memory",
            ),
        ),
    ]
