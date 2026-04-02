import pytest
from django.urls import reverse
from django.contrib import admin
from model_bakery import baker
from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model

User = get_user_model()


# Helper to lazily load models during test collection.
# django.setup() is called explicitly because pytest collects parametrize
# arguments before pytest-django initializes Django — the registry would be
# empty otherwise.
def get_admin_models():
    import django

    django.setup()
    return list(admin.site._registry.items())


def get_edit_models():
    import django

    django.setup()
    return [(m, a) for m, a in admin.site._registry.items() if hasattr(a, "is_edit")]


@pytest.fixture(scope="session", autouse=True)
def setup_baker_generators():
    baker.generators.add("base.fields.MonthField", lambda: date.today().replace(day=1))
    baker.generators.add("base.fields.EuroDecimalField", lambda: Decimal("10.00"))
    baker.generators.add(
        "base.fields.HourMinuteDurationField", lambda: timedelta(hours=1)
    )


@pytest.fixture
def superuser_client(client, db):
    User.objects.create_superuser(username="smoketest", password="smoketest")
    client.login(username="smoketest", password="smoketest")
    return client


@pytest.mark.django_db
class TestAdminSmoke:
    @pytest.mark.parametrize("model, admin_class", get_admin_models())
    def test_changelist_views(self, superuser_client, model, admin_class):
        app = model._meta.app_label
        name = model._meta.model_name
        url = reverse(f"admin:{app}_{name}_changelist")

        response = superuser_client.get(url)
        assert response.status_code == 200

    @pytest.mark.parametrize("model, admin_class", get_admin_models())
    def test_add_views(self, superuser_client, model, admin_class):
        app = model._meta.app_label
        name = model._meta.model_name
        url = reverse(f"admin:{app}_{name}_add")

        response = superuser_client.get(url)
        assert response.status_code == 200

    @pytest.mark.parametrize("model, admin_class", get_edit_models())
    def test_readonly_views(self, superuser_client, model, admin_class):
        app = model._meta.app_label
        name = model._meta.model_name

        obj = model.objects.first() or baker.make(model)
        url = reverse(f"admin:{app}_{name}_change", args=[obj.pk])
        response = superuser_client.get(url)
        assert response.status_code == 200
