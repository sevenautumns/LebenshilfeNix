from django.db import migrations, models


def forwards(apps, schema_editor):
    Employee = apps.get_model("hr", "Employee")
    Employee.objects.filter(maiden_name__isnull=True).update(maiden_name="")
    Employee.objects.filter(personnel_number__isnull=True).update(personnel_number="")
    Employee.objects.filter(social_security_number__isnull=True).update(
        social_security_number=""
    )
    Employee.objects.filter(tax_class__isnull=True).update(tax_class="")
    Employee.objects.filter(risk_assessment__isnull=True).update(risk_assessment="")

    OtherEmployment = apps.get_model("hr", "OtherEmployment")
    OtherEmployment.objects.filter(employer__isnull=True).update(employer="")

    Applicant = apps.get_model("hr", "Applicant")
    Applicant.objects.filter(notice_period__isnull=True).update(notice_period="")
    Applicant.objects.filter(suitability_rating__isnull=True).update(
        suitability_rating=""
    )


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0007_db_index_to_meta_indexes"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="employee",
            name="maiden_name",
            field=models.CharField(blank=True, max_length=255, verbose_name="Geburtsname"),
        ),
        migrations.AlterField(
            model_name="employee",
            name="personnel_number",
            field=models.CharField(
                blank=True,
                max_length=50,
                verbose_name="Personal-Nr. Lohnprogramm",
                help_text="Personalnummer im Lohnprogramm (optional)",
            ),
        ),
        migrations.AlterField(
            model_name="employee",
            name="social_security_number",
            field=models.CharField(
                blank=True,
                max_length=50,
                verbose_name="Sozialversicherungs-Nr.",
                help_text="12-stellige Sozialversicherungsnummer",
            ),
        ),
        migrations.AlterField(
            model_name="employee",
            name="tax_class",
            field=models.CharField(
                blank=True,
                max_length=10,
                verbose_name="Steuerklasse",
            ),
        ),
        migrations.AlterField(
            model_name="employee",
            name="risk_assessment",
            field=models.TextField(blank=True, verbose_name="Erläut. Gefährdungsbeurteilung"),
        ),
        migrations.AlterField(
            model_name="otheremployment",
            name="employer",
            field=models.CharField(
                blank=True, max_length=255, verbose_name="Arbeitgeber (Sonstige)"
            ),
        ),
        migrations.AlterField(
            model_name="applicant",
            name="notice_period",
            field=models.CharField(blank=True, max_length=255, verbose_name="Kündigungsfristen"),
        ),
        migrations.AlterField(
            model_name="applicant",
            name="suitability_rating",
            field=models.CharField(
                blank=True, max_length=255, verbose_name="Einstufung nach Eignung"
            ),
        ),
    ]
