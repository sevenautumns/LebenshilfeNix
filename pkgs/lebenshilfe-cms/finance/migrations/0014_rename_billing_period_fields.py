import base.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0013_monthlycontractcost'),
    ]

    operations = [
        # Payment: drop old index first, then rename+alter field, then add new index
        migrations.RemoveIndex(
            model_name='payment',
            name='payment_payment_date_idx',
        ),
        migrations.RenameField(
            model_name='payment',
            old_name='payment_date',
            new_name='billing_period',
        ),
        migrations.AlterField(
            model_name='payment',
            name='billing_period',
            field=base.fields.MonthField(blank=True, null=True, verbose_name='Abrechnungsdatum'),
        ),
        migrations.AddIndex(
            model_name='payment',
            index=models.Index(fields=['billing_period'], name='payment_billing_period_idx'),
        ),
        migrations.AlterModelOptions(
            name='payment',
            options={
                'verbose_name': 'Zahlung',
                'verbose_name_plural': 'Zahlungen',
                'ordering': ['-billing_period'],
            },
        ),

        # MonthlyContractCost: rename field, update constraint, update verbose names
        migrations.RenameField(
            model_name='monthlycontractcost',
            old_name='month',
            new_name='billing_period',
        ),
        migrations.AlterField(
            model_name='monthlycontractcost',
            name='billing_period',
            field=base.fields.MonthField(verbose_name='Abrechnungsdatum'),
        ),
        migrations.AlterField(
            model_name='monthlycontractcost',
            name='gross_personnel_costs',
            field=base.fields.EuroDecimalField(
                decimal_places=2,
                max_digits=10,
                verbose_name='Tatsächliche Brutto-Personalkosten',
                help_text='Tatsächliche monatliche Kosten inkl. Arbeitgeberanteil',
            ),
        ),
        migrations.RemoveConstraint(
            model_name='monthlycontractcost',
            name='monthlycontractcost_unique_employment_month',
        ),
        migrations.AddConstraint(
            model_name='monthlycontractcost',
            constraint=models.UniqueConstraint(
                fields=('employment', 'billing_period'),
                name='monthlycontractcost_unique_employment_billing_period',
            ),
        ),
        migrations.AlterModelOptions(
            name='monthlycontractcost',
            options={
                'verbose_name': 'Monatliche Vertragskosten',
                'verbose_name_plural': 'Monatliche Vertragskosten',
                'ordering': ['-billing_period'],
            },
        ),
    ]
