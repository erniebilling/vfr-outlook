"""
Rebuild airports_us.json by joining OurAirports airports.csv with runways.csv.

Run from the data/ directory:
    python3 build_airports.py

Sources:
    https://davidmegginson.github.io/ourairports-data/airports.csv
    https://davidmegginson.github.io/ourairports-data/runways.csv

Schema
------
Each airport object has:
  icao  – proper 4-letter ICAO code (e.g. "KPVF"), or the local FAA ident
          when no ICAO code exists (e.g. "7S5").
  faa   – FAA / local identifier (e.g. "S39"). Equals icao for airports whose
          ident already is their ICAO code.

OurAirports sometimes has two rows for the same physical airport: one with the
local ident (ident="S39", gps_code="", icao_code="") and one with the ICAO
code (ident="S39", gps_code="KPVF", icao_code="KPVF").  The build step
collapses these into a single entry with icao="KPVF" and faa="S39".
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

    # ── Pass 1: collect all candidate rows ───────────────────────────────────
    # Key: (lat_4dp, lon_4dp) → best row dict.  "Best" = has an icao_code.
    # We also track the FAA ident (local ident) for each location.
    #
    # Some airports appear twice: once as the local ident row (icao_code=""),
    # and once as the ICAO row (icao_code="KPVF", gps_code="KPVF").
    # We collapse them: prefer the ICAO row for the icao field, keep the local
    # ident as faa.

    # coord_key → {"icao_row": ap, "faa_row": ap}
    by_coord: dict[tuple, dict] = {}

    def _is_us(ap: dict, ident: str) -> bool:
        # K-prefixed US airports are exactly 4 characters (e.g. KBDN, KSEA).
        # Longer K-prefixed idents (e.g. KE-0005) are non-US.
        if (
            (ident.startswith("K") and len(ident) == 4) or
            ident.startswith("PA") or  # Alaska
            ident.startswith("PH") or  # Hawaii
            ident.startswith("PG") or  # Guam
            ident.startswith("TJ") or  # Puerto Rico
            ident.startswith("MB")     # Bahamas adj
        ):
            return True
        return ap.get("iso_country", "") == "US"

    for ap in airports_raw:
        ap_type = ap.get("type", "")
        if ap_type not in KEEP_TYPES:
            continue

        gps_code  = ap.get("gps_code",  "").strip().upper()
        raw_ident = ap.get("ident",     "").strip().upper()
        icao_code = ap.get("icao_code", "").strip().upper() or None

        ident = gps_code or raw_ident
        if not ident:
            continue
        if not _is_us(ap, ident):
            continue

        try:
            lat = round(float(ap["latitude_deg"]),  4)
            lon = round(float(ap["longitude_deg"]), 4)
        except (ValueError, KeyError):
            continue

        key = (lat, lon)
        entry = by_coord.setdefault(key, {"icao_row": None, "faa_row": None, "ap_type": ap_type})

        if icao_code:
            # This row carries the proper ICAO code — prefer it as the icao field.
            entry["icao_row"] = ap
        else:
            # Local-ident row — keep as faa candidate (prefer shorter/earlier if dupes).
            if entry["faa_row"] is None:
                entry["faa_row"] = ap

    # ── Pass 2: emit one record per physical airport ─────────────────────────
    airports = []
    for (lat, lon), entry in by_coord.items():
        icao_row = entry["icao_row"]
        faa_row  = entry["faa_row"]
        ap_type  = entry["ap_type"]

        # Choose which row drives the primary fields
        primary = icao_row or faa_row
        if primary is None:
            continue

        gps_code  = primary.get("gps_code",  "").strip().upper()
        raw_ident = primary.get("ident",     "").strip().upper()
        icao_code = primary.get("icao_code", "").strip().upper() or None

        # icao: use the proper ICAO code if available, else fall back to local ident
        icao = icao_code or gps_code or raw_ident

        # faa: the local ident from whichever row has it; fall back to icao
        if faa_row is not None:
            faa_gps  = faa_row.get("gps_code",  "").strip().upper()
            faa_raw  = faa_row.get("ident",     "").strip().upper()
            faa = faa_gps or faa_raw or icao
        else:
            faa = icao

        elev = None
        try:
            elev = int(float(primary.get("elevation_ft") or "")) if primary.get("elevation_ft") else None
        except ValueError:
            pass

        # Runways indexed under gps_code, raw ident, or icao
        candidates = {gps_code, raw_ident, icao, faa} - {""}
        runways: list[dict] = []
        for c in candidates:
            runways = runways_by_ident.get(c, [])
            if runways:
                break

        max_rwy_length = max((r["length_ft"] for r in runways if r["length_ft"]), default=None)
        _HARD_PREFIXES = ("ASP", "CON", "PEM", "CONC", "ASPH")
        has_hard_surface = any(
            r["surface"] and any(r["surface"].startswith(p) for p in _HARD_PREFIXES)
            for r in runways
        )

        # has_metar: true when the airport has (or can derive) a 4-letter ICAO
        # station ID for the Aviation Weather API.
        # - Explicit icao_code field: use it directly.
        # - 4-letter K-prefixed ident: already ICAO.
        # - 3-letter domestic ident (e.g. "S39"): the METAR API accepts "K"+ident.
        # Derive the station ID used for METAR queries.
        if icao_code:
            metar_id = icao_code
        elif len(icao) == 4 and icao[0].isalpha():
            metar_id = icao
        elif len(icao) == 3 and icao[0].isalpha():
            # 3-char domestic: Aviation Weather accepts K+ident
            metar_id = "K" + icao
        else:
            metar_id = None

        has_metar = metar_id is not None

        airports.append({
            "icao":             icao,
            "faa":              faa,
            "metar_id":         metar_id,
            "name":             primary.get("name", "").strip(),
            "lat":              lat,
            "lon":              lon,
            "elev":             elev,
            "type":             ap_type,
            "runways":          runways,
            "max_rwy_ft":       max_rwy_length,
            "has_hard_surface": has_hard_surface,
            "has_metar":        has_metar,
        })

    airports.sort(key=lambda a: a["icao"])
    print(f"Writing {len(airports):,} airports to {OUT_PATH} …")
    with open(OUT_PATH, "w") as f:
        json.dump(airports, f, separators=(",", ":"))
    print("Done.")


if __name__ == "__main__":
    main()
