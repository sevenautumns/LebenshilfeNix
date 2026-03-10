import environ
import os
from pathlib import Path
from django.utils.translation import gettext_lazy as _
from django.templatetags.static import static

env = environ.Env(
    DEBUG=(bool, False),
)

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = env('SECRET_KEY')
DATABASE_URL = env('DATABASE_URL')

DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

# Application definition
INSTALLED_APPS = [
    "unfold",  # Must be first to override default admin templates
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Eigene Apps:
    "base",
    "hr",
    "pedagogy",
    "finance",
    "members",
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
]

ROOT_URLCONF = 'lebenshilfe.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'lebenshilfe.wsgi.application'

DATABASES = {
    'default': env.db(),
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'de'
TIME_ZONE = 'Europe/Berlin'
USE_I18N = True
USE_TZ = True

LANGUAGES = (
    ("de", _("Deutsch")),
)

# Unfold Configuration
UNFOLD = {
    "SITE_TITLE": "Lebenshilfe Verwaltung",
    "SITE_HEADER": "Lebenshilfe",
    "SITE_LOGO": {
        "light": lambda request: static("logo-light.svg"),
        "dark": lambda request: static("logo-dark.svg"),
    },
    "SHOW_LANGUAGES": False,
    "COLORS": {
        "primary": {
            "50": "#e6f0f7",   # Tint of LH Blau
            "500": "#0069B4",  # LH Blau (Main Brand Color) [cite: 118]
            "600": "#005a9a",  # Shade of LH Blau
            "950": "#001a2d",  # Dark shade of LH Blau
        },
        "base": {
            "50": "#E2E7F3",   # LH Hellblau (Background Color) 
            "100": "#d1d9ea",
            "500": "#7f8da8",
            "900": "#1a1a1a",
            "950": "#000000",  # LH Schwarz
        },
        "font": {
            "subtle-light": "var(--color-base-500)",
            "subtle-dark": "var(--color-base-400)",
            "default-light": "var(--color-base-950)", # LH Schwarz for default text
            "default-dark": "var(--color-base-50)",    # LH Hellblau for dark mode text
            "important-light": "var(--color-primary-500)", # LH Blau for highlights
            "important-dark": "var(--color-base-100)",
        },
    },
}

STATIC_URL = 'static/'
STATIC_ROOT = env('STATIC_ROOT', default=None)
MEDIA_ROOT = env('MEDIA_ROOT', default=None)

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
