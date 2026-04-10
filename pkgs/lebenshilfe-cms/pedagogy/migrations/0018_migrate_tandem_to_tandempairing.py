from django.db import migrations


def migrate_tandem_forward(apps, schema_editor):
    """
    Für jede Supervision mit tandem_id: eine neue Supervision für das Tandem-Kind
    erstellen und beide per TandemPairing verknüpfen.

    tandem + is_tandem_prophylactic existieren hier noch (werden erst in 0019 entfernt).
    total_amount und monthly_installment werden für die neue Tandem-Supervision auf None
    gesetzt – der Calculator muss neu ausgeführt werden.
    """
    Supervision = apps.get_model("pedagogy", "Supervision")
    TandemPairing = apps.get_model("pedagogy", "TandemPairing")

    for sup in Supervision.objects.filter(tandem__isnull=False).select_related(
        "tandem"
    ):
        # Neue Supervision für das Tandem-Kind erstellen
        tandem_sup = Supervision.objects.create(
            student=sup.tandem,
            is_prophylactic=sup.is_tandem_prophylactic,
            caretaker=sup.caretaker,
            school=sup.school,
            class_name=sup.class_name,
            start_date=sup.start_date,
            end_date=sup.end_date,
            weekly_hours=sup.weekly_hours,
            total_amount=None,
            monthly_installment=None,
        )
        TandemPairing.objects.create(
            supervision_a=sup,
            supervision_b=tandem_sup,
        )


def migrate_tandem_backward(apps, schema_editor):
    """
    Umkehrung: TandemPairings auflösen und tandem-Felder wiederherstellen.
    Die neu erstellten Tandem-Supervisions werden gelöscht.
    """
    Supervision = apps.get_model("pedagogy", "Supervision")
    TandemPairing = apps.get_model("pedagogy", "TandemPairing")

    for pairing in TandemPairing.objects.select_related(
        "supervision_a__tandem", "supervision_b__student"
    ):
        sup_a = pairing.supervision_a
        sup_b = pairing.supervision_b
        # supervision_a bekommt tandem + is_tandem_prophylactic zurück
        sup_a.tandem = sup_b.student
        sup_a.is_tandem_prophylactic = sup_b.is_prophylactic
        sup_a.save(update_fields=["tandem", "is_tandem_prophylactic"])
        # supervision_b war neu erstellt → löschen
        pairing.delete()
        sup_b.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("pedagogy", "0017_tandempairing_delete_schulauswertung_schoolreport_and_more"),
    ]

    operations = [
        migrations.RunPython(
            migrate_tandem_forward,
            reverse_code=migrate_tandem_backward,
        ),
    ]
