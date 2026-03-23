from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("base", "0006_alter_person_full_name_delete_costpayerlink"),
    ]

    operations = [
        migrations.AddField(
            model_name="masterdata",
            name="name",
            field=models.CharField(default="", max_length=255, verbose_name="Name"),
            preserve_default=False,
        ),
    ]
