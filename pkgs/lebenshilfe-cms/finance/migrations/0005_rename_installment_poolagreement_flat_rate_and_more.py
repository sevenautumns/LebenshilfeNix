from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0004_alter_costpayer_options_alter_feeagreement_options_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="poolagreement",
            old_name="installment",
            new_name="flat_rate",
        ),
        migrations.AlterField(
            model_name="poolagreement",
            name="flat_rate",
            field=models.DecimalField(
                decimal_places=2,
                help_text="Pauschalentgelt in Euro pro betreutem Fall",
                max_digits=10,
                verbose_name="Pauschalentgelt pro Fall",
            ),
        ),
        migrations.AddField(
            model_name="poolagreement",
            name="max_supervisions",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Anzahl der aktuell erlaubten Betreuungen laut Vereinbarung",
                verbose_name="Max. Betreuungen",
            ),
            preserve_default=False,
        ),
    ]
