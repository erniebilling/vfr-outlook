"""
Rebuild airports_us.json by joining OurAirports airports.csv with runways.csv.

Run from the data/ directory:
    python3 build_airports.py

Sources:
    https://davidmegginson.github.io/ourairports-data/airports.csv
    https://davidmegginson.github.io/ourairports-data/runways.csv
"""

import csv
import json
import urllib.request
from collections import defaultdict
from pathlib import Path

AIRPORTS_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"
RUNWAYS_URL  = "https://davidmegginson.github.io/ourairports-data/runways.csv"
OUT_PATH = Path(__file__).parent / "airports_us.json"

KEEP_TYPES = {"small_airport", "medium_airport", "large_airport"}


def fetch_csv(url: str) -> list[dict]:
    print(f"Fetching {url} …")
    with urllib.request.urlopen(url) as resp:
        lines = resp.read().decode("utf-8").splitlines()
    return list(csv.DictReader(lines))


def main():
    airports_raw = fetch_csv(AIRPORTS_URL)
    runways_raw  = fetch_csv(RUNWAYS_URL)

    # Build runway index: ident -> list of runway dicts
    runways_by_ident: dict[str, list[dict]] = defaultdict(list)
    for rw in runways_raw:
        if rw.get("closed") == "1":
            continue
        ident = rw["airport_ident"].strip().upper()

        length = None
        width  = None
        try:
            length = int(rw["length_ft"]) if rw["length_ft"] else None
        except ValueError:
            pass
        try:
            width = int(rw["width_ft"]) if rw["width_ft"] else None
        except ValueError:
            pass

        # Parse true headings for both ends; derive missing HE from LE if needed
        le_hdg = he_hdg = None
        try:
            le_hdg = round(float(rw["le_heading_degT"]), 1)
        except (ValueError, KeyError, TypeError):
            pass
        try:
            he_hdg = round(float(rw["he_heading_degT"]), 1)
        except (ValueError, KeyError, TypeError):
            pass
        if le_hdg is not None and he_hdg is None:
            he_hdg = round((le_hdg + 180) % 360, 1)
        elif he_hdg is not None and le_hdg is None:
            le_hdg = round((he_hdg + 180) % 360, 1)

        runways_by_ident[ident].append({
            "le":        rw.get("le_ident", "").strip(),
            "he":        rw.get("he_ident", "").strip(),
            "length_ft": length,
            "width_ft":  width,
            "surface":   rw.get("surface", "").strip().upper() or None,
            "lighted":   rw.get("lighted") == "1",
            "le_hdg":    le_hdg,
            "he_hdg":    he_hdg,
        })

    # Build airport list
    airports = []
    for ap in airports_raw:
        ap_type = ap.get("type", "")
        if ap_type not in KEEP_TYPES:
            continue

        gps_code = ap.get("gps_code", "").strip().upper()
        raw_ident = ap.get("ident", "").strip().upper()
        ident = gps_code or raw_ident
        if not ident:
            continue

        # US airports only (K prefix, or US territories P/T/M prefixes, and Alaska/Hawaii)
        if not (
            ident.startswith("K") or
            ident.startswith("PA") or  # Alaska
            ident.startswith("PH") or  # Hawaii
            ident.startswith("PG") or  # Guam
            ident.startswith("TJ") or  # Puerto Rico
            ident.startswith("MB")     # Bahamas adj
        ):
            # Also include domestic identifiers (no K) that are in US
            country = ap.get("iso_country", "")
            if country != "US":
                continue

        lat = lon = elev = None
        try:
            lat  = round(float(ap["latitude_deg"]),  4)
            lon  = round(float(ap["longitude_deg"]), 4)
        except (ValueError, KeyError):
            continue  # skip if no coords
        try:
            elev = int(float(ap["elevation_ft"])) if ap.get("elevation_ft") else None
        except ValueError:
            pass

        # Runways may be indexed under gps_code (e.g. "S39") or raw ident (e.g. "KS39")
        runways = runways_by_ident.get(ident) or runways_by_ident.get(raw_ident) or []

        # Compute derived summaries useful for filtering
        max_rwy_length = max((r["length_ft"] for r in runways if r["length_ft"]), default=None)
        has_hard_surface = any(
            r["surface"] and any(s in (r["surface"] or "") for s in ("ASPH", "CONC", "TURF-GRVL", "GRVL-ASPH"))
            for r in runways
        )

        icao_code = ap.get("icao_code", "").strip().upper() or None

        airports.append({
            "icao":             ident,
            "name":             ap.get("name", "").strip(),
            "lat":              lat,
            "lon":              lon,
            "elev":             elev,
            "type":             ap_type,
            "runways":          runways,
            "max_rwy_ft":       max_rwy_length,
            "has_hard_surface": has_hard_surface,
            "has_metar":        icao_code is not None,
        })

    airports.sort(key=lambda a: a["icao"])
    print(f"Writing {len(airports):,} airports to {OUT_PATH} …")
    with open(OUT_PATH, "w") as f:
        json.dump(airports, f, separators=(",", ":"))
    print("Done.")


if __name__ == "__main__":
    main()
