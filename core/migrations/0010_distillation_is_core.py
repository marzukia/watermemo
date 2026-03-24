from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_alter_distillation_memory"),
    ]

    operations = [
        migrations.AddField(
            model_name="distillation",
            name="is_core",
            field=models.BooleanField(default=False),
        ),
    ]
