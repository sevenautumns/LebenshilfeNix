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

    id_idx = cols["DESTATIS-Schluessel-Staatsangehoerigkeit"]
    iso_idx = cols["ISO-2"]
    name_idx = cols["Staatsname-kurz"]
    nat_idx = cols["Staatsangehoerigkeit"]

    def is_valid_iso(val):
        return isinstance(val, str) and len(val) == 2 and val.isalpha()

    filtered_data = []
    for entry in data["daten"]:
        try:
            raw_id = entry[id_idx]
            iso = entry[iso_idx]

            # Filter: ID unter 900 und valider ISO-Code
            if int(raw_id) < 900 and is_valid_iso(iso):
                filtered_data.append(entry)
        except (ValueError, TypeError):
            continue

    filtered_data.sort(key=lambda x: int(x[id_idx]))

    countries = [(e[iso_idx], e[name_idx]) for e in filtered_data]
    nationalities = [(e[id_idx], e[nat_idx]) for e in filtered_data]

    return countries, nationalities

COUNTRY_CHOICES, NATIONALITY_CHOICES = get_destatis_choices()
