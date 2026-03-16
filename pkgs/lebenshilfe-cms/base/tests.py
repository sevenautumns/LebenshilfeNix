from datetime import timedelta
from django.test import TestCase
from django.db import models
from django.contrib.admin.sites import AdminSite
from .widgets import EuroDecimalWidget, HourMinuteDurationWidget
from .admin import BaseModelAdmin

class WidgetTests(TestCase):
    def test_euro_decimal_widget_attributes(self):
        """Prüft, ob das Euro-Icon korrekt in den Attributen gesetzt ist."""
        widget = EuroDecimalWidget()
        self.assertEqual(widget.attrs["prefix_icon"], "euro_symbol")
        self.assertIn("border-base-200", widget.attrs["class"])

    def test_duration_widget_decompress(self):
        """Prüft die Aufteilung von timedelta in Stunden und Minuten."""
        widget = HourMinuteDurationWidget()
        
        self.assertEqual(widget.decompress(timedelta(hours=1, minutes=35)), [1, 35])
        self.assertEqual(widget.decompress(timedelta(hours=40)), [40, 0])
        self.assertEqual(widget.decompress(None), [None, None])

    def test_duration_widget_value_from_datadict(self):
        """Prüft, ob HH und MM korrekt zu HH:MM:00 für Django zusammengesetzt werden."""
        widget = HourMinuteDurationWidget()
        data = {'demand_0': '1', 'demand_1': '35'}
        
        self.assertEqual(widget.value_from_datadict(data, {}, 'demand'), '1:35:00')

    def test_duration_widget_empty_input(self):
        """Prüft das Verhalten bei leeren Formularfeldern."""
        widget = HourMinuteDurationWidget()
        data = {'demand_0': '', 'demand_1': ''}
        self.assertIsNone(widget.value_from_datadict(data, {}, 'demand'))


class AdminDisplayTests(TestCase):
    def setUp(self):
        self.site = AdminSite()

    def test_universal_duration_display_format(self):
        """Prüft die statische Factory-Methode für die Tabellenansicht."""
        
        class MockModel(models.Model):
            demand = models.DurationField()

            class Meta:
                app_label = 'base'
        
        class MockAdmin(BaseModelAdmin):
            pass
        
        display_func = BaseModelAdmin.duration_display("demand", "Test Bedarf")
        admin_inst = MockAdmin(MockModel, self.site)

        obj_ok = MockModel(demand=timedelta(hours=1, minutes=35))
        self.assertEqual(display_func(admin_inst, obj_ok), "1:35 Std.")

        obj_zero = MockModel(demand=timedelta(hours=2))
        self.assertEqual(display_func(admin_inst, obj_zero), "2:00 Std.")

        obj_none = MockModel(demand=None)
        self.assertEqual(display_func(admin_inst, obj_none), "-")
