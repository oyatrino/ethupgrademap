#!/usr/bin/env python3
"""Enrich upgrades.seed.json into upgrades.json.

Hybrid pipeline: the seed file is hand-curated (names, the city<->star pairing,
status, dates). This script auto-fills the coordinates that would be tedious and
error-prone to maintain by hand:

  * execution-layer cities  -> lat/lon via OpenStreetMap Nominatim
  * consensus-layer stars   -> RA/Dec via the CDS Sesame name resolver

Anything that does not resolve (e.g. a not-yet-catalogued star name like "Gloas")
falls back to a curated override table and emits a warning rather than failing,
so a single unresolved name never blocks a refresh.
"""

import argparse
import json
import re
import sys
import time

import requests

SEED_PATH = "upgrades.seed.json"
OUT_PATH = "upgrades.json"
COUNT_PATH = "upgrade-count.json"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
SESAME_URL = "https://cds.unistra.fr/cgi-bin/nph-sesame/-oI"
USER_AGENT = "EthUpgradeMap/1.0 (https://github.com/oyatrino/ethupgrademap)"

# City strings that geocode poorly; map to an unambiguous query.
CITY_OVERRIDES = {}

# Display name -> the identifier to send to the Sesame resolver.
STAR_QUERY = {
    "Fulu (Zeta Cassiopeiae)": "zet Cas",
}

# Stars Sesame cannot resolve (future / non-catalogue names) -> curated RA/Dec.
# Use (None, None) to keep an entry unplotted until real coordinates exist.
STAR_OVERRIDES = {
    # "Gloas" is a proposed consensus-fork name, not a catalogued star. Sesame
    # returns a spurious fuzzy match, so pin it to "no coordinates yet".
    "Gloas": (None, None),
}


def geocode_city(query):
    """Return (lat, lon) for a city via Nominatim, or (None, None)."""
    q = CITY_OVERRIDES.get(query, query)
    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={"q": q, "format": "json", "limit": 1},
            headers={"User-Agent": USER_AGENT},
            timeout=20,
        )
        resp.raise_for_status()
        results = resp.json()
    except (requests.RequestException, ValueError) as exc:
        print(f"  WARNING: geocode failed for {query!r}: {exc}", file=sys.stderr)
        return None, None
    if not isinstance(results, list) or not results:
        print(f"  WARNING: no geocode result for {query!r}", file=sys.stderr)
        return None, None
    first = results[0]
    if not isinstance(first, dict):
        return None, None
    try:
        return round(float(first["lat"]), 4), round(float(first["lon"]), 4)
    except (KeyError, TypeError, ValueError):
        return None, None


def resolve_star(name):
    """Return (ra, dec) in degrees for a star via Sesame, or (None, None)."""
    if name in STAR_OVERRIDES:
        ra, dec = STAR_OVERRIDES[name]
        return ra, dec
    query = STAR_QUERY.get(name, name)
    try:
        resp = requests.get(
            f"{SESAME_URL}?{requests.utils.quote(query)}",
            headers={"User-Agent": USER_AGENT},
            timeout=20,
        )
        resp.raise_for_status()
        text = resp.text
    except requests.RequestException as exc:
        print(f"  WARNING: star resolve failed for {name!r}: {exc}", file=sys.stderr)
        return None, None
    # Sesame returns a line like: %J 297.69582730 +08.86832120 = ...
    m = re.search(r"%J\s+([-+]?\d+\.?\d*)\s+([-+]?\d+\.?\d*)", text)
    if not m:
        print(f"  WARNING: could not resolve star {name!r} (query {query!r})", file=sys.stderr)
        return None, None
    return round(float(m.group(1)), 3), round(float(m.group(2)), 3)


def enrich(seed):
    """Return the enriched upgrades list."""
    upgrades = seed.get("upgrades")
    if not isinstance(upgrades, list):
        print("ERROR: seed has no 'upgrades' list.", file=sys.stderr)
        sys.exit(1)

    out = []
    for u in upgrades:
        if not isinstance(u, dict):
            continue
        entry = {
            "name": u.get("name"),
            "combined": u.get("combined"),
            "status": u.get("status") or "planned",
            "date": u.get("date"),
            "execution": None,
            "consensus": None,
        }

        ex = u.get("execution")
        if isinstance(ex, dict) and ex.get("city"):
            lat, lon = geocode_city(ex["city"])
            print(f"  {entry['name']}: {ex['city']} -> ({lat}, {lon})")
            entry["execution"] = {"fork": ex.get("fork"), "city": ex["city"], "lat": lat, "lon": lon}
            time.sleep(1)  # be polite to Nominatim

        cl = u.get("consensus")
        if isinstance(cl, dict) and cl.get("star"):
            ra, dec = resolve_star(cl["star"])
            print(f"  {entry['name']}: ★ {cl['star']} -> RA {ra}, Dec {dec}")
            entry["consensus"] = {"fork": cl.get("fork"), "star": cl["star"], "ra": ra, "dec": dec}

        out.append(entry)
    return out


def main():
    parser = argparse.ArgumentParser(description="Enrich the upgrade seed into upgrades.json.")
    parser.add_argument("--seed", default=SEED_PATH)
    parser.add_argument("--out", default=OUT_PATH)
    parser.add_argument("--count", default=COUNT_PATH)
    args = parser.parse_args()

    with open(args.seed, encoding="utf-8") as f:
        seed = json.load(f)

    upgrades = enrich(seed)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"upgrades": upgrades}, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {args.out} with {len(upgrades)} upgrades.")

    live = sum(1 for u in upgrades if u.get("status") == "live")
    count = {"schemaVersion": 1, "label": "upgrades", "message": f"{len(upgrades)} ({live} live)", "color": "blue"}
    with open(args.count, "w", encoding="utf-8") as f:
        json.dump(count, f, indent=2)
        f.write("\n")
    print(f"Wrote {args.count}.")


if __name__ == "__main__":
    main()
