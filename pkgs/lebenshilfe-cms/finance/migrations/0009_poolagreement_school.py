from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0008_alter_salaryagreement_table"),
        ("pedagogy", "__first__"),
    ]

    operations = [
        migrations.AddField(
            model_name="poolagreement",
            name="school",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="pool_agreements",
                to="pedagogy.school",
                verbose_name="Schule",
            ),
            preserve_default=False,
        ),
    ]
