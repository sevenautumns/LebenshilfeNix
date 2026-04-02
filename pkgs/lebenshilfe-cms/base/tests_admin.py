from decimal import Decimal
from datetime import date, timedelta

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from model_bakery import baker

from base.fields import EuroDecimalField, HourMinuteDurationField, MonthField

baker.generators.add(EuroDecimalField, lambda: Decimal("10.00"))
baker.generators.add(MonthField, lambda: date(2024, 1, 1))
baker.generators.add(HourMinuteDurationField, lambda: timedelta(hours=1, minutes=30))

User = get_user_model()


class AdminSmokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="smoketest", password="smoketest"
        )

    def setUp(self):
        self.client.login(username="smoketest", password="smoketest")

    def test_changelist_views(self):
        for model, _ in admin.site._registry.items():
            app = model._meta.app_label
            name = model._meta.model_name
            url = reverse(f"admin:{app}_{name}_changelist")
            with self.subTest(view=f"{app}/{name} changelist"):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_add_views(self):
        for model, _ in admin.site._registry.items():
            app = model._meta.app_label
            name = model._meta.model_name
            url = reverse(f"admin:{app}_{name}_add")
            with self.subTest(view=f"{app}/{name} add"):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_readonly_views(self):
        for model, admin_class in admin.site._registry.items():
            # Only test models that implement the EditModeMixin
            if not hasattr(admin_class, "is_edit"):
                continue

            app = model._meta.app_label
            name = model._meta.model_name

            obj = model.objects.first() or baker.make(model)
            object_id = obj.pk if obj else 1

            url = reverse(f"admin:{app}_{name}_change", args=[object_id])
            with self.subTest(view=f"{app}/{name} readonly"):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

    def test_change_views(self):
        for model, admin_class in admin.site._registry.items():
            if not hasattr(admin_class, "is_edit"):
                continue

            app = model._meta.app_label
            name = model._meta.model_name

            obj = model.objects.first() or baker.make(model)
            object_id = obj.pk if obj else 1

            url = reverse(f"admin:{app}_{name}_change", args=[object_id])
            with self.subTest(view=f"{app}/{name} change"):
                response = self.client.get(f"{url}?edit=1")
                self.assertEqual(response.status_code, 200)
