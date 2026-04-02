from datetime import date, timedelta

from django.test import TestCase

from hr.models import Applicant, Employee, TrainingRecord, TrainingType


# --- TrainingRecord.is_valid Tests ---


class TrainingRecordTests(TestCase):
    def setUp(self):
        self.employee = Employee.objects.create(first_name="Max", last_name="Muster")
        self.training_type = TrainingType.objects.create(name="Erste Hilfe")
        self.today = date.today()

    def _make_record(self, valid_from, valid_to=None):
        return TrainingRecord(
            employee=self.employee,
            training_type=self.training_type,
            valid_from=valid_from,
            valid_to=valid_to,
        )

    def test_is_valid_current(self):
        """Ein Nachweis mit Vergangenheit als Start und Zukunft als Ende ist gültig."""
        record = self._make_record(
            valid_from=self.today - timedelta(days=365),
            valid_to=self.today + timedelta(days=365),
        )
        self.assertTrue(record.is_valid)

    def test_is_valid_permanent(self):
        """Ein Nachweis ohne Enddatum ist dauerhaft gültig."""
        record = self._make_record(
            valid_from=self.today - timedelta(days=100),
            valid_to=None,
        )
        self.assertTrue(record.is_valid)

    def test_is_valid_expired(self):
        """Ein Nachweis, dessen Enddatum gestern war, ist nicht mehr gültig."""
        record = self._make_record(
            valid_from=self.today - timedelta(days=365),
            valid_to=self.today - timedelta(days=1),
        )
        self.assertFalse(record.is_valid)

    def test_is_valid_not_yet_started(self):
        """Ein Nachweis, der erst morgen beginnt, ist noch nicht gültig."""
        record = self._make_record(
            valid_from=self.today + timedelta(days=1),
            valid_to=self.today + timedelta(days=365),
        )
        self.assertFalse(record.is_valid)

    def test_is_valid_expires_today(self):
        """Ein Nachweis, der heute ausläuft, ist noch gültig (inklusiv)."""
        record = self._make_record(
            valid_from=self.today - timedelta(days=365),
            valid_to=self.today,
        )
        self.assertTrue(record.is_valid)

    def test_is_valid_starts_today(self):
        """Ein Nachweis, der heute beginnt, ist bereits gültig (inklusiv)."""
        record = self._make_record(
            valid_from=self.today,
            valid_to=self.today + timedelta(days=365),
        )
        self.assertTrue(record.is_valid)


# --- Applicant.desired_hours_summary Tests ---


class ApplicantDesiredHoursTests(TestCase):
    def _make_applicant(self, min_hours=None, max_hours=None):
        return Applicant(
            first_name="Test",
            last_name="Person",
            application_date=date.today(),
            desired_hours_min=min_hours,
            desired_hours_max=max_hours,
        )

    def test_both_min_and_max(self):
        """Prüft die Ausgabe, wenn Min und Max gesetzt sind."""
        applicant = self._make_applicant(
            min_hours=timedelta(hours=2),
            max_hours=timedelta(hours=4),
        )
        self.assertEqual(applicant.desired_hours_summary, "2:00–4:00 Std.")

    def test_only_min(self):
        """Prüft die Ausgabe, wenn nur ein Mindestwert gesetzt ist."""
        applicant = self._make_applicant(min_hours=timedelta(hours=2))
        self.assertEqual(applicant.desired_hours_summary, "ab 2:00 Std.")

    def test_only_max(self):
        """Prüft die Ausgabe, wenn nur ein Maximalwert gesetzt ist."""
        applicant = self._make_applicant(max_hours=timedelta(hours=4))
        self.assertEqual(applicant.desired_hours_summary, "bis 4:00 Std.")

    def test_neither(self):
        """Prüft die Ausgabe, wenn kein Stundenwunsch angegeben ist."""
        applicant = self._make_applicant()
        self.assertEqual(applicant.desired_hours_summary, "–")

    def test_minutes_formatted_with_leading_zero(self):
        """Prüft, dass Minuten immer zweistellig formatiert werden."""
        applicant = self._make_applicant(
            min_hours=timedelta(hours=1, minutes=5),
            max_hours=timedelta(hours=2, minutes=30),
        )
        self.assertEqual(applicant.desired_hours_summary, "1:05–2:30 Std.")
