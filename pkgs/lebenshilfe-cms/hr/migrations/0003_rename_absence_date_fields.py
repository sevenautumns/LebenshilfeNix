from django.db import migrations, models
import django.db.models.functions.comparison
import django.db.models.expressions


class Migration(migrations.Migration):
    dependencies = [
        ("hr", "0002_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="absence",
            old_name="start",
            new_name="start_date",
        ),
        migrations.RenameField(
            model_name="absence",
            old_name="end",
            new_name="end_date",
        ),
        migrations.RemoveConstraint(
            model_name="absence",
            name="absence_end_after_start",
        ),
        migrations.AddConstraint(
            model_name="absence",
            constraint=models.CheckConstraint(
                condition=models.Q(start_date__isnull=True)
                | models.Q(end_date__isnull=True)
                | models.Q(end_date__gte=models.F("start_date")),
                name="absence_end_after_start",
            ),
        ),
    ]
