from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0007_add_embedding_vector"),
    ]

    operations = [
        migrations.DeleteModel(name="EventMemory"),
    ]
