from django.db import migrations, models
import django.db.models.expressions


class Migration(migrations.Migration):
    dependencies = [
        ("pedagogy", "0001_initial"),
    ]

    operations = [
        # Supervision: start → start_date, end → end_date
        migrations.RenameField(
            model_name="supervision",
            old_name="start",
            new_name="start_date",
        ),
        migrations.RenameField(
            model_name="supervision",
            old_name="end",
            new_name="end_date",
        ),
        migrations.RemoveConstraint(
            model_name="supervision",
            name="supervision_end_after_start",
        ),
        migrations.AddConstraint(
            model_name="supervision",
            constraint=models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="supervision_end_after_start",
            ),
        ),
        # Request: start → start_date, valid_to → end_date
        migrations.RenameField(
            model_name="request",
            old_name="start",
            new_name="start_date",
        ),
        migrations.RenameField(
            model_name="request",
            old_name="valid_to",
            new_name="end_date",
        ),
        migrations.RemoveConstraint(
            model_name="request",
            name="request_valid_to_after_start",
        ),
        migrations.AddConstraint(
            model_name="request",
            constraint=models.CheckConstraint(
                condition=models.Q(end_date__isnull=True)
                | models.Q(end_date__gte=models.F("start_date")),
                name="request_end_date_after_start_date",
            ),
        ),
    ]
