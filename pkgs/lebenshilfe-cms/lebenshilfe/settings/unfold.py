from django.templatetags.static import static

UNFOLD = {
    "SITE_TITLE": "Lebenshilfe Verwaltung",
    "SITE_HEADER": "Lebenshilfe",
    "SITE_LOGO": {
        "light": lambda request: static("logo-light.svg"),
        "dark": lambda request: static("logo-dark.svg"),
    },
    "ACCOUNT": {
        "navigation": [
            {
                "title": "Gehe zu Nextcloud",
                "link": "https://nextcloud.lebenshilfe-uslar.de",
            },
        ],
    },
    "SITE_URL": (),
    "SHOW_LANGUAGES": False,
    "COLORS": {
        "primary": {
            "50": "#e6f0f7",  # Tint of LH Blau
            "500": "#0069B4",  # LH Blau (Main Brand Color) [cite: 118]
            "600": "#005a9a",  # Shade of LH Blau
            "950": "#001a2d",  # Dark shade of LH Blau
        },
    },
}
