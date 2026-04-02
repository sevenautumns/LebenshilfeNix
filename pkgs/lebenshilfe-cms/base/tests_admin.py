from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

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
