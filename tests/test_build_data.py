from unittest.mock import MagicMock, patch

from scripts import build_data


# ---------- resolve_star (Sesame parsing) ----------

def test_resolve_star_parses_sesame():
    resp = MagicMock(text="# Altair\n%J 297.69582730 +08.86832120 = ...\n", status_code=200)
    resp.raise_for_status = lambda: None
    with patch("scripts.build_data.requests.get", return_value=resp):
        ra, dec = build_data.resolve_star("Altair")
    assert ra == 297.696
    assert dec == 8.868


def test_resolve_star_unresolved_returns_none():
    resp = MagicMock(text="#!Sesame: nothing found\n", status_code=200)
    resp.raise_for_status = lambda: None
    with patch("scripts.build_data.requests.get", return_value=resp):
        assert build_data.resolve_star("Gloas") == (None, None)


def test_resolve_star_uses_override_without_network():
    with patch.dict(build_data.STAR_OVERRIDES, {"FakeStar": (12.5, -30.0)}, clear=False):
        with patch("scripts.build_data.requests.get") as get:
            assert build_data.resolve_star("FakeStar") == (12.5, -30.0)
            get.assert_not_called()


# ---------- geocode_city ----------

def test_geocode_city_parses_result():
    resp = MagicMock(status_code=200)
    resp.raise_for_status = lambda: None
    resp.json = lambda: [{"lat": "52.52000", "lon": "13.40500"}]
    with patch("scripts.build_data.requests.get", return_value=resp):
        assert build_data.geocode_city("Berlin, Germany") == (52.52, 13.405)


def test_geocode_city_empty_result_returns_none():
    resp = MagicMock(status_code=200)
    resp.raise_for_status = lambda: None
    resp.json = lambda: []
    with patch("scripts.build_data.requests.get", return_value=resp):
        assert build_data.geocode_city("Nowhere") == (None, None)


# ---------- enrich ----------

def _seed():
    return {
        "upgrades": [
            {"name": "London", "combined": None, "status": "live", "date": "2021-08-05",
             "execution": {"fork": "London", "city": "London, United Kingdom"}, "consensus": None},
            {"name": "Shapella", "combined": "Shapella", "status": "live", "date": "2023-04-12",
             "execution": {"fork": "Shanghai", "city": "Shanghai, China"},
             "consensus": {"fork": "Capella", "star": "Capella"}},
            {"name": "X", "execution": None, "consensus": None},  # missing status -> default
        ]
    }


def test_enrich_fills_coords_and_defaults_status():
    with patch("scripts.build_data.geocode_city", return_value=(1.0, 2.0)), \
         patch("scripts.build_data.resolve_star", return_value=(80.0, 46.0)), \
         patch("scripts.build_data.time.sleep"):
        out = build_data.enrich(_seed())

    london, shapella, x = out
    assert london["execution"] == {"fork": "London", "city": "London, United Kingdom", "lat": 1.0, "lon": 2.0}
    assert london["consensus"] is None
    assert shapella["consensus"] == {"fork": "Capella", "star": "Capella", "ra": 80.0, "dec": 46.0}
    assert x["status"] == "planned"  # default applied when seed omits status
