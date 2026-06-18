# Periplus — design spec

Status: approved (design), pending spec review. Date: 2026-06-18.

## Summary

**Periplus** is a reusable, upptime-style GitHub template for building interactive
"history maps": a chronological sequence of named, dated points placed on one or more
configurable basemaps — Earth, the Moon, Mars, or the celestial sphere — connected as a
route, with timeline playback and a date slider.

`tezosprotocolmap` and `ethupgrademap` become the first two consumers. Other examples the
design must accommodate: crewed/robotic Moon landings, Mars rovers & landers, and personal
or historical travel routes (e.g. Magellan's circumnavigation).

The name (Greek *períplous*) is an ancient document listing places in the order a voyage
reaches them — i.e. exactly this tool's data model.

## Goals

- Eliminate the heavy duplication between the two existing map repos (frontend engine,
  Python pipeline, CI workflows, README/SEO scaffolding).
- Let a new map be created from a template with only: a config file, a data-source
  adapter, and generated data — no copied engine code.
- Auto-upgrade consumers when the core releases a new version, via reviewable PRs.

## Non-goals (YAGNI)

- No published npm/PyPI packages (served straight from the repo — see Distribution).
- No general GIS/analysis features; this renders an ordered set of placed points only.
- No editing UI; data is produced by each consumer's build step.

## Architecture — three repos

1. **`oyatrino/periplus`** — the versioned **core**:
   - `dist/periplus.js` — hand-maintained frontend engine (no build step).
   - `periplus/` — Python package (enrichment, canonical-JSON IO + validation, renderers).
   - `.github/workflows/*.yml` — reusable workflows (`build`, `test`, `update-check`).
   - Released via git tags (`v1.4.2`); jsDelivr serves `dist/periplus.js` by tag.
2. **`oyatrino/periplus-template`** — a "Use this template" consumer skeleton.
3. **Consumers** — `ethupgrademap` (pilot) and `tezosprotocolmap`, refactored to consume
   the core.

## The canonical data contract

The engine only ever consumes `map-data.json` in this shape. Each item is placed on zero
or more basemaps via `placements`, so one item can appear on several (e.g. an Ethereum
upgrade on both `earth` and `sky`):

```jsonc
{
  "items": [
    {
      "name": "Shapella",
      "date": "2023-04-12",          // ISO date or null
      "status": "live",              // free-form; drives marker colour via config
      "pairing": "Shanghai ⇄ Capella", // optional, shown in popups
      "placements": [
        { "map": "earth", "lat": 31.23, "lon": 121.47, "label": "Shanghai",
          "popup": { "Execution": "Shanghai", "Activated": "2023-04-12" } },
        { "map": "sky",   "ra": 79.17, "dec": 46.0,   "label": "Capella",
          "popup": { "Consensus": "Capella" } }
      ]
    }
  ]
}
```

- A globe-only map (Tezos) emits a single `earth` placement per item.
- The route/trail, playback order, and slider all key off `date` (then array order).
- `popup` is an ordered key→value map the engine renders generically (escaped).

## Basemaps

A basemap is declared in config as `{ id, type, ... }`:

- `type: "tiles"` — an XYZ tile layer: `earth` (OSM), `moon`, `mars` (planetary tile
  URLs, e.g. OpenPlanetaryMap / USGS). Differs only by `tileUrl` + `attribution` + `crs`.
- `type: "celestial"` — the built-in star-chart renderer (RA/Dec, constellations, bright
  stars, Summer Triangle). The reference-sky dataset ships in the core; consumers enable
  it by listing a `sky` basemap.

The header **basemap switcher** replaces the current ad-hoc mode toggle; with one basemap
it is hidden.

## Consumer repo anatomy

After extraction a consumer holds only what is unique:

- **`periplus.config.json`** — title, theme/colours, `basemaps`, status→colour map, links,
  SEO/OG, favicon, and the **pinned core version**.
- **`sources/source.py`** — the only inherently custom code: a `fetch() -> items[]`
  adapter that may call core enrichment helpers (geocode, star-resolve). Examples:
  Tezos (octez naming + teztnets + TzKT), ETH (curated seed + Nominatim + Sesame).
- **`docs/index.html`** — thin: loads `periplus.js@<version>` from jsDelivr, plus the
  config and `map-data.json`.
- **`.github/workflows/`** — two thin files that `uses:` the core's reusable workflows.
- Generated artifacts: `map-data.json`, count badge JSON, static PNGs.

## The core in detail

- **Frontend engine (`dist/periplus.js`)** — basemap rendering (tiles + celestial),
  markers, chronological route, **playback control**, **date slider**, generic popups,
  legends, basemap switcher, zoom caps, SEO/favicon injection, the celestial reference sky.
- **Python package (`periplus/`)** — Nominatim geocode, CDS Sesame star-resolve,
  canonical-JSON read/write + schema validation, count-badge writer, and cartopy/matplotlib
  renderers (tile-basemap map, star chart, pairings figure). Built to the project's
  external-data conventions (null-safe, type-checked, polite rate-limiting).
- **Reusable workflows** — `build.yml` (install the core via
  `pip install git+https://github.com/oyatrino/periplus@<pinned-version>`, then run the
  consumer's `source.py` → enrich → validate → render), `test.yml`, `update-check.yml`
  (the updater bot). Because a consumer calls these with `uses: …@<version>`, the workflow
  definition and the pip-installed core are pinned to the same version.

## Versioning & the updater bot

Consumers **pin an exact core version** (in `periplus.config.json` and their `uses:` refs).
A scheduled **`update-check`** workflow declares `permissions: { contents: write,
pull-requests: write }` and compares the pinned version to the latest core release; if newer
it opens an **"⬆ Upgrade periplus to vX.Y.Z"** PR that bumps the jsDelivr version, the
pip ref, and the `uses:` refs, with release notes. CI re-runs on the PR; a human merges.

This needs **no PAT**: a probe on 2026-06-18 confirmed the oyatrino org allows a workflow
with an explicit `permissions:` block to push a branch and open a PR (the org keeps only the
*default* token read-only; `can_approve_pull_request_reviews` is enabled).

## Migration plan (ethupgrademap is the pilot)

1. Extract the core from eth's (richer) frontend + Python into `oyatrino/periplus`; tag
   `v0.1.0`.
2. Stand up `oyatrino/periplus-template`.
3. Refactor `ethupgrademap` to consume the core; verify the live map is behaviourally
   identical (both basemaps, playback, slider, popups). This is the real-world test.
4. Migrate `tezosprotocolmap` the same way.
5. Wire the `update-check` bot into both consumers; tag core `v1.0.0`.

## Testing

- Core Python: unit tests for enrichment (mocked Nominatim/Sesame), canonical-JSON
  validation, and the renderers (smoke).
- Contract: a JSON-schema validator for `map-data.json`, run in `build.yml` so a malformed
  consumer dataset fails CI.
- Pilot acceptance: ethupgrademap renders identically before/after the refactor.
- Updater: dry-run of `update-check` opening a no-op upgrade PR (proven viable by the probe).
