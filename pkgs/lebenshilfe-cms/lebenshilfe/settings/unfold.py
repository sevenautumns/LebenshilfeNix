from django.templatetags.static import static

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

