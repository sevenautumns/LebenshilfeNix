from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("pedagogy", "0003_alter_request_options_alter_school_options_and_more"),
    ]

    operations = [
        migrations.DeleteModel(
            name="PoolSchoolAgreement",
        ),
    ]
