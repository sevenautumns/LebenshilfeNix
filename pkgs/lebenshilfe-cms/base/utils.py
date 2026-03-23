import json
from pathlib import Path
from django.conf import settings


def get_destatis_choices():
    file_path = (
        Path(settings.BASE_DIR)
        / "base"
        / "data"
        / "destatis_nationalities_2024-08-01.json"
    )

    try:
        with file_path.open(encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return [], []

    cols = {s["spaltennameTechnisch"]: i for i, s in enumerate(data["spalten"])}

    raw_data = [
        entry
        for entry in data["daten"]
        if entry[cols["ISO-2"]] and entry[cols["ISO-2"]] != "··"
    ]

    countries = [(e[cols["ISO-2"]], e[cols["Staatsname-kurz"]]) for e in raw_data]
    nationalities = [
        (
            e[cols["DESTATIS-Schluessel-Staatsangehoerigkeit"]],
            e[cols["Staatsangehoerigkeit"]],
        )
        for e in raw_data
    ]

    return (
        sorted(countries, key=lambda x: x[1]),
        sorted(nationalities, key=lambda x: x[1]),
    )


COUNTRY_CHOICES, NATIONALITY_CHOICES = get_destatis_choices()
