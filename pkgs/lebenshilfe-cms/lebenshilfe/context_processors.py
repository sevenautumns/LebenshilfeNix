from django.conf import settings


def nextcloud_status(request):
    return {"NC_ACTIVE": getattr(settings, "NC_ACTIVE", False)}
