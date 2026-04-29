"""
Download open-source weather icons (Bas Milius weather-icons, MIT licensed)
and save them under public/icons/ using MeteoSwiss-style code filenames so
the existing /api/icon/{code} endpoint and frontend WMO_TO_METEO mapping
keep working without changes.

Source: https://github.com/basmilius/weather-icons
License: MIT (see LICENSE-icons.md)

Run from the repo root:
    python download_open_source_icons.py
"""

import os
import sys
import urllib.request
import urllib.error

# Static (non-animated) fill-style icons — much lighter on low-end GPUs
# (e.g. Raspberry Pi) than the animated variants.
BASE_URL = (
    "https://raw.githubusercontent.com/basmilius/weather-icons/dev/"
    "production/fill/svg-static/"
)

ICON_DIR = os.path.join("public", "icons")

# Map MeteoSwiss code → Bas Milius icon name (without .svg extension).
# Codes match the ones referenced in WMO_TO_METEO inside public/app.js.
# Day codes: 1-42, night codes: 101-142 (where they differ from day).
MAPPING: dict[int, str] = {
    # Clear / mostly clear
    1:   "clear-day",
    101: "clear-night",
    2:   "partly-cloudy-day",
    102: "partly-cloudy-night",
    # Partly to fully cloudy
    3:   "partly-cloudy-day",
    103: "partly-cloudy-night",
    5:   "overcast-day",
    105: "overcast-night",
    # Drizzle / light rain
    7:   "drizzle",
    # Rain
    8:   "rain",
    9:   "extreme-rain",
    # Snow
    13:  "snow",
    14:  "snow",
    15:  "extreme-snow",
    # Showers
    17:  "partly-cloudy-day-rain",
    18:  "partly-cloudy-day-rain",
    19:  "extreme-rain",
    # Thunderstorms
    20:  "thunderstorms-day-rain",
    21:  "thunderstorms-day-extreme-rain",
    23:  "thunderstorms",
    # Fog
    25:  "fog",
    # Freezing rain / sleet
    26:  "sleet",
}


def download_one(code: int, name: str) -> bool:
    """Download a single icon and save it as {code}.svg. Returns True on success."""
    url = f"{BASE_URL}{name}.svg"
    out_path = os.path.join(ICON_DIR, f"{code}.svg")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "meteo-globe-icons/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        with open(out_path, "wb") as f:
            f.write(data)
        print(f"  OK  {code:>3} <- {name}.svg ({len(data):>5} bytes)")
        return True
    except urllib.error.HTTPError as e:
        print(f"  ERR {code:>3} <- {name}.svg  (HTTP {e.code})", file=sys.stderr)
    except Exception as e:
        print(f"  ERR {code:>3} <- {name}.svg  ({e})", file=sys.stderr)
    return False


def main() -> int:
    if not os.path.isdir(ICON_DIR):
        print(f"Creating {ICON_DIR}/")
        os.makedirs(ICON_DIR, exist_ok=True)

    print(f"Downloading {len(MAPPING)} Bas Milius icons -> {ICON_DIR}/")
    print(f"Source: {BASE_URL}")
    print()

    failed = 0
    for code in sorted(MAPPING):
        if not download_one(code, MAPPING[code]):
            failed += 1

    print()
    if failed:
        print(f"Done with {failed} failure(s).", file=sys.stderr)
        return 1
    print(f"Done. {len(MAPPING)} icons saved.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
