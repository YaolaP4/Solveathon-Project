"""Unit tests for the USAspending historical-award check (no network)."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import config  # noqa: E402
from award_history import NC_DHHS, classify, parse_alns, verdict  # noqa: E402

CFG = config.load_agency()["layer5_award_history"]


def test_recipient_names_are_classified():
    cases = {
        "NORTH CAROLINA DEPARTMENT OF HEALTH & HUMAN SERVICES": "state_agency",
        "PUBLIC HEALTH, ILLINOIS DEPARTMENT OF": "state_agency",
        "TEXAS HEALTH & HUMAN SERVICES COMMISSION": "state_agency",
        "NEW YORK CITY DEPARTMENT OF HEALTH AND MENTAL HYGIENE": "local_government",
        "UNIVERSITY OF NORTH CAROLINA AT CHAPEL HILL": "university",
        "YALE UNIV": "university",
        "WASHINGTON UNIVERSITY, THE": "university",
        "EASTERN BAND OF CHEROKEE INDIANS": "tribal",
        "NATIONAL ACADEMY OF SCIENCES": "nonprofit_or_other",
        "MULTIPLE RECIPIENTS": "unclassified",
    }
    assert {n: classify(n) for n in cases} == cases


def test_nc_dhhs_name_variants_match():
    for n in ["NORTH CAROLINA DEPARTMENT OF HEALTH & HUMAN SERVICES",
              "HEALTH AND HUMAN SERVICES, NORTH CAROLINA DEPARTMENT OF"]:
        assert NC_DHHS.search(n)
    assert not NC_DHHS.search("NORTH CAROLINA DEPARTMENT OF PUBLIC INSTRUCTION")


def test_parse_alns():
    assert parse_alns("93.917|HIV Care;93.243|SAMHSA") == ["93.243", "93.917"]
    assert parse_alns("") == []


def row(**kw):
    base = {"total": 100.0, "state_agency": 0.0, "university": 0.0, "tribal": 0.0, "local_government": 0.0,
            "nonprofit_or_other": 0.0, "unclassified": 0.0, "nc_dhhs": 0.0, "error": ""}
    base.update(kw)
    return pd.Series(base)


def test_verdicts():
    assert verdict(row(total=0.0), CFG).startswith("no awards found")
    assert verdict(row(nc_dhhs=CFG["nc_dhhs_min_usd"], state_agency=50), CFG) == "NC DHHS has received awards"
    # A tiny NC DHHS amount under a broad listing is not evidence.
    assert verdict(row(nc_dhhs=1.0, university=90, state_agency=1), CFG) == "mostly universities"
    assert verdict(row(state_agency=30, university=60), CFG) == "other state agencies win this"
    assert verdict(row(unclassified=80, university=20), CFG).startswith("unclear")
    assert verdict(row(total=0.0, error="not a standard assistance listing number"), CFG).startswith("unknown")
