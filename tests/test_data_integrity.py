import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALID_STATUS = {"live", "scheduled", "planned"}


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def test_upgrades_json_well_formed():
    data = load("upgrades.json")
    ups = data["upgrades"]
    assert ups, "expected at least one upgrade"

    for u in ups:
        assert u["name"], "every upgrade needs a name"
        assert u["status"] in VALID_STATUS, f"{u['name']}: bad status {u['status']!r}"
        assert u["execution"] is not None or u["consensus"] is not None, \
            f"{u['name']}: must map at least one layer"

        ex = u["execution"]
        if ex is not None:
            assert ex["fork"] and ex["city"]
            # coords either both present (numbers) or both null
            assert (ex["lat"] is None) == (ex["lon"] is None)

        cl = u["consensus"]
        if cl is not None:
            assert cl["fork"] and cl["star"]
            assert (cl["ra"] is None) == (cl["dec"] is None)
            if cl["ra"] is not None:
                assert 0 <= cl["ra"] <= 360
                assert -90 <= cl["dec"] <= 90


def test_seed_and_output_align():
    seed = load("upgrades.seed.json")["upgrades"]
    out = load("upgrades.json")["upgrades"]
    assert [u["name"] for u in seed] == [u["name"] for u in out], \
        "seed and enriched output must list the same upgrades in the same order"


def test_count_badge_matches():
    data = load("upgrades.json")["upgrades"]
    count = load("upgrade-count.json")
    live = sum(1 for u in data if u["status"] == "live")
    assert count["message"] == f"{len(data)} ({live} live)"
