from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0009_poolagreement_school"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="poolagreement",
            name="max_supervisions",
        ),
        migrations.AddField(
            model_name="poolagreement",
            name="approved_supervisions",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Anzahl der genehmigten Betreuungen laut Vereinbarung",
                verbose_name="Genehmigte Betreuungen",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="poolagreement",
            name="prophylactic_supervisions",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Anzahl der prophylaktischen Betreuungen laut Vereinbarung",
                verbose_name="Prophylaktische Betreuungen",
            ),
            preserve_default=False,
        ),
    ]
