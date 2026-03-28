import environ
from pathlib import Path
from django.utils.translation import gettext_lazy as _

env = environ.Env(
    DEBUG=(bool, False),
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = env("SECRET_KEY")
DATABASE_URL = env("DATABASE_URL")

DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# Application definition
INSTALLED_APPS = [
    "unfold",  # Must be first to override default admin templates
    "unfold.contrib.filters",
    # Allauth
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.nextcloud",
    # Generally requried
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Own Apps:
    "base",
    "hr",
    "pedagogy",
    "finance",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Allauth
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "lebenshilfe.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "lebenshilfe.context_processors.nextcloud_status",
            ],
        },
    },
]

WSGI_APPLICATION = "lebenshilfe.wsgi.application"

DATABASES = {
    "default": env.db(),
}

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "de"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True

LANGUAGES = (("de", _("Deutsch")),)

LOCALE_PATHS = [
    BASE_DIR / "locale",
]

STATIC_URL = "static/"
STATIC_ROOT = env("STATIC_ROOT", default=None)
MEDIA_ROOT = env("MEDIA_ROOT", default=None)

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

from lebenshilfe.settings.unfold import *  # noqa
from lebenshilfe.settings.allauth import *  # noqa
