from datetime import timedelta

from django.db import migrations

import base.fields


def decimal_to_timedelta(decimal_hours):
    """Convert a Decimal hours value (e.g. 20.50) to a timedelta."""
    if decimal_hours is None:
        return None
    total_seconds = int(float(decimal_hours) * 3600)
    return timedelta(seconds=total_seconds)


def migrate_hours_to_duration(apps, schema_editor):
    Employment = apps.get_model("hr", "Employment")
    OtherEmployment = apps.get_model("hr", "OtherEmployment")
    Applicant = apps.get_model("hr", "Applicant")

    for obj in Employment.objects.all():
        obj.working_hours_duration = decimal_to_timedelta(obj.working_hours_decimal)
        obj.save(update_fields=["working_hours_duration"])

    for obj in OtherEmployment.objects.all():
        obj.working_hours_duration = decimal_to_timedelta(obj.working_hours_decimal)
        obj.save(update_fields=["working_hours_duration"])

    for obj in Applicant.objects.all():
        changed = []
        if obj.desired_hours_min_decimal is not None:
            obj.desired_hours_min_duration = decimal_to_timedelta(obj.desired_hours_min_decimal)
            changed.append("desired_hours_min_duration")
        if obj.desired_hours_max_decimal is not None:
            obj.desired_hours_max_duration = decimal_to_timedelta(obj.desired_hours_max_decimal)
            changed.append("desired_hours_max_duration")
        if changed:
            obj.save(update_fields=changed)


def migrate_hours_to_decimal(apps, schema_editor):
    """Reverse: convert timedelta back to decimal hours."""
    Employment = apps.get_model("hr", "Employment")
    OtherEmployment = apps.get_model("hr", "OtherEmployment")
    Applicant = apps.get_model("hr", "Applicant")

    for obj in Employment.objects.all():
        if obj.working_hours_duration is not None:
            obj.working_hours_decimal = round(obj.working_hours_duration.total_seconds() / 3600, 2)
            obj.save(update_fields=["working_hours_decimal"])

    for obj in OtherEmployment.objects.all():
        if obj.working_hours_duration is not None:
            obj.working_hours_decimal = round(obj.working_hours_duration.total_seconds() / 3600, 2)
            obj.save(update_fields=["working_hours_decimal"])

    for obj in Applicant.objects.all():
        changed = []
        if obj.desired_hours_min_duration is not None:
            obj.desired_hours_min_decimal = round(obj.desired_hours_min_duration.total_seconds() / 3600, 2)
            changed.append("desired_hours_min_decimal")
        if obj.desired_hours_max_duration is not None:
            obj.desired_hours_max_decimal = round(obj.desired_hours_max_duration.total_seconds() / 3600, 2)
            changed.append("desired_hours_max_decimal")
        if changed:
            obj.save(update_fields=changed)


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0018_alter_employee_citizenship_and_more"),
    ]

    operations = [
        # --- Step 1: Add new duration columns (nullable) alongside old decimal columns ---
        migrations.AddField(
            model_name="employment",
            name="working_hours_duration",
            field=base.fields.HourMinuteDurationField(
                null=True,
                blank=True,
                verbose_name="Stundenumfang",
                help_text="Wöchentlicher Stundenumfang laut Arbeitsvertrag",
            ),
        ),
        migrations.AddField(
            model_name="otheremployment",
            name="working_hours_duration",
            field=base.fields.HourMinuteDurationField(
                null=True,
                blank=True,
                verbose_name="Stundenumfang",
            ),
        ),
        migrations.AddField(
            model_name="applicant",
            name="desired_hours_min_duration",
            field=base.fields.HourMinuteDurationField(
                null=True,
                blank=True,
                verbose_name="Stundenwunsch (von)",
            ),
        ),
        migrations.AddField(
            model_name="applicant",
            name="desired_hours_max_duration",
            field=base.fields.HourMinuteDurationField(
                null=True,
                blank=True,
                verbose_name="Stundenwunsch (bis)",
            ),
        ),
        # --- Step 2: Rename old decimal columns so they coexist during data migration ---
        migrations.RenameField(
            model_name="employment",
            old_name="working_hours",
            new_name="working_hours_decimal",
        ),
        migrations.RenameField(
            model_name="otheremployment",
            old_name="working_hours",
            new_name="working_hours_decimal",
        ),
        migrations.RenameField(
            model_name="applicant",
            old_name="desired_hours_min",
            new_name="desired_hours_min_decimal",
        ),
        migrations.RenameField(
            model_name="applicant",
            old_name="desired_hours_max",
            new_name="desired_hours_max_decimal",
        ),
        # --- Step 3: Migrate data decimal → timedelta ---
        migrations.RunPython(migrate_hours_to_duration, reverse_code=migrate_hours_to_decimal),
        # --- Step 4: Remove old decimal columns ---
        migrations.RemoveField(model_name="employment", name="working_hours_decimal"),
        migrations.RemoveField(model_name="otheremployment", name="working_hours_decimal"),
        migrations.RemoveField(model_name="applicant", name="desired_hours_min_decimal"),
        migrations.RemoveField(model_name="applicant", name="desired_hours_max_decimal"),
        # --- Step 5: Rename duration columns to final names ---
        migrations.RenameField(
            model_name="employment",
            old_name="working_hours_duration",
            new_name="working_hours",
        ),
        migrations.RenameField(
            model_name="otheremployment",
            old_name="working_hours_duration",
            new_name="working_hours",
        ),
        migrations.RenameField(
            model_name="applicant",
            old_name="desired_hours_min_duration",
            new_name="desired_hours_min",
        ),
        migrations.RenameField(
            model_name="applicant",
            old_name="desired_hours_max_duration",
            new_name="desired_hours_max",
        ),
        # --- Step 6: Make Employment and OtherEmployment non-nullable (Applicant stays nullable) ---
        migrations.AlterField(
            model_name="employment",
            name="working_hours",
            field=base.fields.HourMinuteDurationField(
                verbose_name="Stundenumfang",
                help_text="Wöchentlicher Stundenumfang laut Arbeitsvertrag",
            ),
        ),
        migrations.AlterField(
            model_name="otheremployment",
            name="working_hours",
            field=base.fields.HourMinuteDurationField(verbose_name="Stundenumfang"),
        ),
    ]
