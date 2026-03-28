from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("base", "0002_postcode_to_charfield"),
    ]

    operations = [
        migrations.RenameField(
            model_name="phone",
            old_name="telephone_number",
            new_name="number",
        ),
    ]
