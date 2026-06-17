#!/usr/bin/env python3
"""Render static images from upgrades.json.

  starchart.png  consensus layer: named stars on an RA/Dec celestial plane
  globe.png      execution layer: cities on a Robinson world map (needs cartopy)
  pairings.png   both projections stacked, with lines linking each portmanteau's
                 city to its paired star (needs cartopy)

The star chart needs only matplotlib, so it renders anywhere. The globe and the
pairings figure import cartopy lazily and are skipped with a warning if it is
not installed.
"""

import argparse
import json
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

COLOR_LIVE = "#1f77b4"
COLOR_SCHEDULED = "#ff7f0e"
COLOR_PLANNED = "#9aa0b5"
COLOR_STAR = "#ffe08a"
COLOR_ROUTE = "#888888"
SKY_BG = "#05060f"


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("upgrades", [])


def status_color(status):
    return {"live": COLOR_LIVE, "scheduled": COLOR_SCHEDULED}.get(status, COLOR_PLANNED)


def _stars(upgrades):
    return [u for u in upgrades if u.get("consensus") and u["consensus"].get("ra") is not None]


def _cities(upgrades):
    return [u for u in upgrades if u.get("execution") and u["execution"].get("lat") is not None]


def draw_starchart(ax, upgrades):
    ax.set_facecolor(SKY_BG)
    ax.set_xlim(368, -8)  # RA increases to the left; small margin so edge labels fit
    ax.set_ylim(-90, 90)
    for ra in range(0, 361, 30):
        ax.axvline(ra, color="#2a3358", lw=0.4, zorder=1)
    for dec in range(-60, 61, 30):
        ax.axhline(dec, color="#2a3358", lw=0.4, zorder=1)
    ax.axhline(0, color="#3c4a85", lw=0.8, ls="--", zorder=1)

    stars = _stars(upgrades)
    if len(stars) > 1:
        xs = [u["consensus"]["ra"] for u in stars]
        ys = [u["consensus"]["dec"] for u in stars]
        ax.plot(xs, ys, color="#6f7bd0", lw=0.8, ls=(0, (2, 4)), alpha=0.6, zorder=2)
    for u in stars:
        ra, dec = u["consensus"]["ra"], u["consensus"]["dec"]
        ax.scatter([ra], [dec], s=70, marker="*", color=COLOR_STAR, edgecolor="#fff7d6", lw=0.5, zorder=4)
        ax.annotate(u["consensus"]["star"].split(" ")[0], (ra, dec), textcoords="offset points",
                    xytext=(6, 4), fontsize=7, color="#e8e8ff", zorder=5)
    ax.set_xlabel("Right ascension (°)", color="#aab", fontsize=8)
    ax.set_ylabel("Declination (°)", color="#aab", fontsize=8)
    ax.tick_params(colors="#778", labelsize=7)
    for s in ax.spines.values():
        s.set_color("#2a3358")


def generate_starchart(upgrades, output, dpi):
    fig, ax = plt.subplots(figsize=(11, 6))
    fig.patch.set_facecolor(SKY_BG)
    draw_starchart(ax, upgrades)
    ax.set_title("Ethereum consensus-layer upgrades — named stars", color="#dde", fontsize=11)
    fig.tight_layout()
    fig.savefig(output, dpi=dpi, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"Wrote {output}")


def draw_globe(ax, upgrades, ccrs, cfeature):
    ax.set_global()
    ax.add_feature(cfeature.OCEAN, facecolor="#ddeeff")
    ax.add_feature(cfeature.LAND, facecolor="#f0f0f0")
    ax.add_feature(cfeature.BORDERS, linewidth=0.3, edgecolor="#cccccc")
    ax.add_feature(cfeature.COASTLINE, linewidth=0.4, edgecolor="#aaaaaa")

    cities = _cities(upgrades)
    pts = [(u["execution"]["lon"], u["execution"]["lat"]) for u in cities]
    for i in range(len(pts) - 1):
        ax.annotate("", xy=pts[i + 1], xytext=pts[i],
                    xycoords=ccrs.PlateCarree()._as_mpl_transform(ax),
                    textcoords=ccrs.PlateCarree()._as_mpl_transform(ax),
                    arrowprops=dict(arrowstyle="->", color=COLOR_ROUTE, alpha=0.4, lw=0.6), zorder=3)
    for u in cities:
        lon, lat = u["execution"]["lon"], u["execution"]["lat"]
        ax.plot(lon, lat, "o", color=status_color(u["status"]), markersize=5,
                transform=ccrs.PlateCarree(), zorder=5)
        ax.annotate(u["execution"]["city"].split(",")[0], xy=(lon, lat),
                    xycoords=ccrs.PlateCarree()._as_mpl_transform(ax),
                    xytext=(6, -4), textcoords="offset points", fontsize=6,
                    fontweight="bold", color="#333", zorder=6)


def _try_cartopy():
    try:
        import cartopy.crs as ccrs
        import cartopy.feature as cfeature
        return ccrs, cfeature
    except ImportError:
        print("  WARNING: cartopy not installed; skipping globe/pairings.", file=sys.stderr)
        return None, None


def generate_globe(upgrades, output, dpi):
    ccrs, cfeature = _try_cartopy()
    if not ccrs:
        return
    fig = plt.figure(figsize=(12, 6))
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.Robinson())
    draw_globe(ax, upgrades, ccrs, cfeature)
    ax.set_title("Ethereum execution-layer upgrades — Devcon/Devconnect cities", fontsize=11)
    fig.tight_layout(pad=0.5)
    fig.savefig(output, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {output}")


def generate_pairings(upgrades, output, dpi):
    """Both projections stacked, with lines linking each portmanteau city<->star."""
    ccrs, cfeature = _try_cartopy()
    if not ccrs:
        return
    fig = plt.figure(figsize=(11, 9))
    ax_g = fig.add_subplot(2, 1, 1, projection=ccrs.Robinson())
    draw_globe(ax_g, upgrades, ccrs, cfeature)
    ax_g.set_title("Execution layer (cities)", fontsize=10)
    ax_s = fig.add_subplot(2, 1, 2)
    ax_s.set_facecolor(SKY_BG)
    draw_starchart(ax_s, upgrades)
    ax_s.set_title("Consensus layer (stars)", fontsize=10)

    # Link paired city -> star across the two axes, in figure coordinates.
    geo = ccrs.PlateCarree()
    for u in upgrades:
        ex, cl = u.get("execution"), u.get("consensus")
        if not (ex and cl and ex.get("lat") is not None and cl.get("ra") is not None):
            continue
        x_g, y_g = ax_g.projection.transform_point(ex["lon"], ex["lat"], geo)
        p_g = fig.transFigure.inverted().transform(ax_g.transData.transform((x_g, y_g)))
        p_s = fig.transFigure.inverted().transform(ax_s.transData.transform((cl["ra"], cl["dec"])))
        line = plt.Line2D([p_g[0], p_s[0]], [p_g[1], p_s[1]], transform=fig.transFigure,
                          color="#c060d0", lw=0.7, alpha=0.6, ls=":", zorder=10)
        fig.add_artist(line)
        if u.get("combined"):
            fig.text((p_g[0] + p_s[0]) / 2, (p_g[1] + p_s[1]) / 2, u["combined"],
                     fontsize=6, color="#c060d0", ha="center", va="center", zorder=11)

    fig.savefig(output, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {output}")


def main():
    parser = argparse.ArgumentParser(description="Generate static upgrade maps.")
    parser.add_argument("--data", default="upgrades.json")
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--only", choices=["starchart", "globe", "pairings"], help="render just one")
    args = parser.parse_args()

    upgrades = load(args.data)
    print(f"Loaded {len(upgrades)} upgrades from {args.data}")

    if args.only in (None, "starchart"):
        generate_starchart(upgrades, "starchart.png", args.dpi)
    if args.only in (None, "globe"):
        generate_globe(upgrades, "globe.png", args.dpi)
    if args.only in (None, "pairings"):
        generate_pairings(upgrades, "pairings.png", args.dpi)


if __name__ == "__main__":
    main()
