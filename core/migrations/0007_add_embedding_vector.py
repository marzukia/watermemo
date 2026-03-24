from django.db import migrations
import pgvector.django


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0006_distillation_add_memory_fk"),
    ]

    operations = [
        migrations.AddField(
            model_name="memory",
            name="embedding",
            field=pgvector.django.VectorField(dimensions=768, null=True),
        ),
        migrations.AddField(
            model_name="distillation",
            name="embedding",
            field=pgvector.django.VectorField(dimensions=768, null=True),
        ),
    ]
