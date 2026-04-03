from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("hr", "0019_working_hours_to_duration"),
    ]

    operations = [
        migrations.RenameField(
            model_name="employment",
            old_name="working_hours",
            new_name="weekly_hours",
        ),
        migrations.RenameField(
            model_name="otheremployment",
            old_name="working_hours",
            new_name="weekly_hours",
        ),
        migrations.AddField(
            model_name="employment",
            name="work_days_override",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                verbose_name="Arbeitstage (Überschreibung)",
                help_text="Überschreibt die Arbeitstage aus den Stammdaten für dieses Arbeitsverhältnis",
            ),
        ),
        migrations.AddField(
            model_name="employment",
            name="month_override",
            field=models.DecimalField(
                blank=True,
                null=True,
                max_digits=5,
                decimal_places=2,
                verbose_name="Monate (Überschreibung)",
                help_text="Überschreibt die rechnerischen Vertragsmonate für dieses Arbeitsverhältnis",
            ),
        ),
    ]
