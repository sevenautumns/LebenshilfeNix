from decimal import Decimal
from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase, RequestFactory
from django.db import models
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.utils import translation

from .models import Person
from .widgets import EuroDecimalWidget, HourMinuteDurationWidget
from .fields import EuroDecimalField, HourMinuteDurationField
from .mixins import EditModeMixin, AdminDisplayMixin
from .admin import BaseModelAdmin


# --- Mock Modelle und Admins für Mixin-Tests ---

class MockFieldModel(models.Model):
    """Ein temporäres Modell, um die Custom Fields und das Display Mixin zu testen."""
    amount = EuroDecimalField(max_digits=10, decimal_places=2, verbose_name="Betrag")
    time_spent = HourMinuteDurationField(verbose_name="Zeitaufwand")

    class Meta:
        app_label = "base"
        managed = False # Verhindert, dass Django versucht, eine Tabelle dafür anzulegen


class MockAdminWithEdit(BaseModelAdmin):
    """Erbt bereits von EditModeMixin via BaseModelAdmin."""
    pass


class MockAdminWithDisplay(BaseModelAdmin):
    """Erbt bereits von AdminDisplayMixin via BaseModelAdmin."""
    list_display = ["id", "amount", "time_spent"]
    readonly_fields = ["amount"]
    fields = ["id", "amount", "time_spent"]


# --- Widget Tests ---

class WidgetTests(TestCase):
    def test_euro_decimal_widget_attributes(self):
        """Prüft, ob das Euro-Icon korrekt in den Attributen gesetzt ist."""
        widget = EuroDecimalWidget()
        self.assertEqual(widget.attrs["prefix_icon"], "euro_symbol")
        self.assertIn("border-base-200", widget.attrs["class"])

    def test_duration_widget_decompress(self):
        """Prüft die Aufteilung von timedelta und Strings in Stunden und Minuten."""
        widget = HourMinuteDurationWidget()

        # Timedelta
        self.assertEqual(widget.decompress(timedelta(hours=1, minutes=35)), [1, 35])
        self.assertEqual(widget.decompress(timedelta(hours=40)), [40, 0])
        
        # String Parse (z.B. aus der Datenbank)
        self.assertEqual(widget.decompress("01:35:00"), [1, 35])
        
        # Leere Werte
        self.assertEqual(widget.decompress(None), [None, None])
        self.assertEqual(widget.decompress(""), [None, None])

    def test_duration_widget_value_from_datadict(self):
        """Prüft, ob HH und MM korrekt zu timedelta für Django zusammengesetzt werden."""
        widget = HourMinuteDurationWidget()
        
        # Normaler Input
        data = {"demand_0": "1", "demand_1": "35"}
        self.assertEqual(widget.value_from_datadict(data, {}, "demand"), timedelta(hours=1, minutes=35))

        # Nur Minuten
        data_mins = {"demand_0": "", "demand_1": "45"}
        self.assertEqual(widget.value_from_datadict(data_mins, {}, "demand"), timedelta(minutes=45))

    def test_duration_widget_empty_input(self):
        """Prüft das Verhalten bei leeren Formularfeldern."""
        widget = HourMinuteDurationWidget()
        data = {"demand_0": "", "demand_1": ""}
        self.assertIsNone(widget.value_from_datadict(data, {}, "demand"))


# --- Field Tests ---

class FieldTests(TestCase):
    def test_euro_decimal_field_formfield(self):
        """Prüft, ob dem Field das korrekte Widget zugewiesen wird."""
        field = EuroDecimalField(max_digits=5, decimal_places=2)
        form_field = field.formfield()
        self.assertIsInstance(form_field.widget, EuroDecimalWidget)

    def test_euro_decimal_field_admin_format(self):
        """Prüft die Formatierung inkl. Lokalisierung."""
        field = EuroDecimalField(max_digits=10, decimal_places=2)
        
        with translation.override('de'):
            self.assertEqual(field.get_admin_format(Decimal('1234.50')), "1234,50 €")
            self.assertEqual(field.get_admin_format(Decimal('42')), "42,00 €")
            
        self.assertEqual(field.get_admin_format(None), "-")

    def test_hour_minute_duration_field_formfield(self):
        """Prüft, ob dem Field das korrekte Widget zugewiesen wird."""
        field = HourMinuteDurationField()
        form_field = field.formfield()
        self.assertIsInstance(form_field.widget, HourMinuteDurationWidget)

    def test_hour_minute_duration_field_admin_format(self):
        """Prüft die Formatierung der Dauer in Stunden und Minuten."""
        field = HourMinuteDurationField()
        self.assertEqual(field.get_admin_format(timedelta(hours=1, minutes=5)), "1:05 Std.")
        self.assertEqual(field.get_admin_format(timedelta(hours=40)), "40:00 Std.")
        self.assertEqual(field.get_admin_format(timedelta(minutes=45)), "0:45 Std.")
        self.assertEqual(field.get_admin_format(None), "-")


# --- Mixin Tests ---

class EditModeMixinTests(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = MockAdminWithEdit(Person, self.site)
        self.factory = RequestFactory()
        self.user = User.objects.create_superuser('admin', 'admin@test.com', 'pass')

    def _get_request(self, path="/", edit_param=False):
        url = path + "?edit=1" if edit_param else path
        request = self.factory.get(url)
        request.user = self.user
        return request

    def test_is_edit(self):
        """Prüft, ob der Bearbeitungsmodus via Query-Parameter erkannt wird."""
        self.assertTrue(self.admin.is_edit(self._get_request(edit_param=True)))
        self.assertFalse(self.admin.is_edit(self._get_request(edit_param=False)))

    def test_has_edit_action_permission(self):
        """Der Bearbeiten-Button soll nur sichtbar sein, wenn wir NICHT im Edit-Modus sind."""
        req_view = self._get_request(edit_param=False)
        req_edit = self._get_request(edit_param=True)
        
        self.assertTrue(self.admin.has_edit_action_permission(req_view))
        self.assertFalse(self.admin.has_edit_action_permission(req_edit))

    @patch("base.mixins.reverse")
    def test_edit_action_redirect(self, mock_reverse):
        """Prüft, ob die Action korrekt auf die URL mit dem ?edit=1 Parameter weiterleitet."""
        mock_reverse.return_value = "/admin/base/person/1/change/"
        req = self._get_request()
        
        # Mock Person hat ID 1
        response = self.admin.edit_action(req, object_id=1)
        
        self.assertEqual(response.status_code, 302)
        self.assertIn("?edit=1", response.url)
        self.assertIn("/admin/base/person/1/change/", response.url)

    def test_has_change_permission(self):
        """
        has_change_permission soll überschrieben werden und auf Detail-Ebene
        nur True sein, wenn der edit=1 Parameter gesetzt ist.
        """
        person = Person(id=1, first_name="Max", last_name="Mustermann")
        
        req_view = self._get_request(edit_param=False)
        req_edit = self._get_request(edit_param=True)

        # Globale Berechtigung (obj=None) bleibt erhalten (Superuser = True)
        self.assertTrue(self.admin.has_change_permission(req_view, obj=None))

        # Auf Objekt-Ebene hängt es vom edit-Parameter ab
        self.assertFalse(self.admin.has_change_permission(req_view, obj=person))
        self.assertTrue(self.admin.has_change_permission(req_edit, obj=person))


class AdminDisplayMixinTests(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = MockAdminWithDisplay(MockFieldModel, self.site)
        self.factory = RequestFactory()
        self.user = User.objects.create_superuser('admin', 'admin@test.com', 'pass')
        self.mock_obj = MockFieldModel(
            id=1, 
            amount=Decimal('50.00'), 
            time_spent=timedelta(hours=2)
        )

    def test_methods_generated_on_init(self):
        """
        Prüft, ob das Mixin die `display_amount` und `display_time_spent` 
        Methoden automatisch zur Laufzeit an die Admin-Klasse gebunden hat.
        """
        self.assertTrue(hasattr(self.admin, "display_amount"))
        self.assertTrue(hasattr(self.admin, "display_time_spent"))
        
        # Testen ob die generierte Funktion das richtige Format liefert
        self.assertEqual(self.admin.display_time_spent(self.mock_obj), "2:00 Std.")
        self.assertEqual(self.admin.display_amount.short_description, "Betrag")

    @patch.object(MockAdminWithDisplay, 'has_change_permission', return_value=False)
    def test_field_replacement_without_change_permission(self, mock_permission):
        """
        Wenn der Nutzer keine Schreibrechte (Change Permission) hat,
        sollen die Eingabefelder durch ihre formatierte Display-Version ersetzt werden.
        """
        request = self.factory.get("/")
        request.user = self.user

        # 1. Test get_readonly_fields
        ro_fields = self.admin.get_readonly_fields(request, obj=self.mock_obj)
        # Ursprünglich war "amount" readonly, jetzt sollte "display_amount" dort stehen
        self.assertIn("display_amount", ro_fields)
        self.assertNotIn("amount", ro_fields)
        # Ausserdem sollte "display_time_spent" dazugekommen sein
        self.assertIn("display_time_spent", ro_fields)

        # 2. Test get_fields
        fields = self.admin.get_fields(request, obj=self.mock_obj)
        self.assertIn("display_amount", fields)
        self.assertIn("display_time_spent", fields)
        self.assertNotIn("amount", fields)
        self.assertNotIn("time_spent", fields)

    def test_list_display_replacement(self):
        """
        In der Listenansicht sollen Felder, die eine generierte `display_` Funktion
        haben, automatisch in get_list_display ausgetauscht werden.
        """
        request = self.factory.get("/")
        list_display = self.admin.get_list_display(request)
        
        # 'id' hat kein get_admin_format, bleibt also gleich
        self.assertIn("id", list_display)
        # Die Custom Fields sollten durch die display_ Methoden ersetzt sein
        self.assertIn("display_amount", list_display)
        self.assertIn("display_time_spent", list_display)
        self.assertNotIn("amount", list_display)
        self.assertNotIn("time_spent", list_display)
