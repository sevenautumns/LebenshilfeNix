from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns

urlpatterns = [
    # Required for internationalization views
    path("i18n/", include("django.conf.urls.i18n")),
]

# i18n_patterns adds the language prefix (e.g., /de/admin/) 
# and ensures the translation engine is active.
urlpatterns += i18n_patterns(
    path('', admin.site.urls),
)
