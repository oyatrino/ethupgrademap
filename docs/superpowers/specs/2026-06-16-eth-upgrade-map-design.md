# Ethereum Upgrade Map — design

Status: implemented (v1). Date: 2026-06-16.

## Goal

A standalone side project (`oyatrino/ethupgrademap`) mapping Ethereum's dual-layer
upgrade naming onto two projections, mirroring the structure of
`oyatrino/tezosprotocolmap`:

- **Execution layer → Devcon/Devconnect host cities** on a globe, drawn as a
  chronological travel route (Berlin, London, Paris, Shanghai, Cancún, Prague, …).
- **Consensus layer → stars** (alphabetical: Altair, Bellatrix, Capella, …) on a
  celestial RA/Dec chart.
- Post-Merge upgrades are portmanteaus pairing one city + one star (Shapella =
  Shanghai + Capella). Pairing is surfaced in popups and a static pairings figure.
- References EIP-8133 (execution-layer naming convention).

## Decisions

- **Repo:** new standalone repo, GitHub Pages from `main/docs`.
- **Data:** hybrid — `upgrades.seed.json` is hand-curated (names, city/star pairing,
  status, dates); `scripts/build_data.py` auto-fills coordinates (Nominatim for
  cities, CDS Sesame for stars) into `upgrades.json`. Unresolved names fall back to a
  curated override table and warn rather than fail.
- **Star chart rendering:** Leaflet on `L.CRS.Simple`, mapping RA→x, Dec→y (decision
  A1). One library, consistent with the globe; the ~6–9 stars suit a stylised chart.
- **Pairing visualisation:** mode switch between Globe and Star chart (no live
  cross-projection overlay). Pairing is conveyed via popups and the static
  `pairings.png` figure, which stacks both projections and draws a line from each
  portmanteau's city to its paired star.
- **Updates:** twice-a-year `update.yml` workflow rebuilds data + images and uploads
  them as an artifact (the org blocks Actions from pushing/opening PRs), to be
  downloaded and committed by hand.

## Data model (`upgrades.json`)

Array of upgrades in chronological order. Each: `name`, `combined` (portmanteau or
null), `status` (`live` | `scheduled` | `planned`), `date` (or null), and the two
layer objects (`execution` may be null pre-Merge for CL-only; `consensus` may be null
for EL-only):

- `execution`: `{ fork, city, lat, lon }`
- `consensus`: `{ fork, star, ra, dec }`

Coordinates are null when not yet resolvable (e.g. the proposed "Gloas" star), which
keeps the entry unplotted until real values exist.

## Components

- `docs/index.html` — interactive dual-projection map (Leaflet ×2 + mode switch).
  Reads `upgrades.json` at runtime; no build step.
- `scripts/build_data.py` — seed → enriched data + count badge JSON.
- `scripts/generate_maps.py` — `starchart.png` (matplotlib), `globe.png` and
  `pairings.png` (cartopy, imported lazily so the star chart runs without it).
- `.github/workflows/test.yml` — pytest on push.
- `.github/workflows/update.yml` — twice-a-year rebuild → artifact.

## Testing

- `tests/test_build_data.py` — Sesame/Nominatim parsing and `enrich()` with network
  mocked; status defaulting; override path.
- `tests/test_data_integrity.py` — `upgrades.json` schema, seed/output alignment,
  count badge consistency.
