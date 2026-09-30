import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from clean_data import clean


def _raw():
    return pd.DataFrame([
        {"opportunity_id": "1", "opportunity_title": " Health  Grant ", "agency_name": "HHS",
         "summary_description": "<p>Fund &amp; serve</p>", "applicant_types": "State governments|state governments|Nonprofits",
         "applicant_eligibility_description": "", "close_date": "2026-10-15", "is_forecast": "False",
         "award_floor": "$1,000", "award_ceiling": "5,000.50", "estimated_total_program_funding": "",
         "forecasted_close_date": ""},
        {"opportunity_id": "2", "opportunity_title": "Forecast", "agency_name": "NIH",
         "summary_description": "x", "applicant_types": "", "applicant_eligibility_description": "y",
         "close_date": "", "is_forecast": "True", "award_floor": "9", "award_ceiling": "3",
         "estimated_total_program_funding": "", "forecasted_close_date": "2027-01-31"},
        {"opportunity_id": "1", "opportunity_title": "dup id", "agency_name": "HHS",
         "summary_description": "", "applicant_types": "", "applicant_eligibility_description": "",
         "close_date": "bad-date", "is_forecast": "", "award_floor": "", "award_ceiling": "",
         "estimated_total_program_funding": "", "forecasted_close_date": ""},
    ])


def test_clean_basics():
    out, rep = clean(_raw())
    assert len(out) == 2 and rep["duplicate_ids_removed"] == 1
    r = out.iloc[0]
    assert r.opportunity_title == "Health Grant"
    assert r.summary_description == "Fund & serve"
    assert r.applicant_types == "State governments|Nonprofits"
    assert r.award_floor == 1000 and r.award_ceiling == 5000.5
    assert r.track == "open" and out.iloc[1].track == "forecast"


def test_forecast_not_missing_deadline_and_flags():
    out, _ = clean(_raw())
    assert not out.iloc[1].missing_deadline
    assert out.iloc[1].award_range_inconsistent
    assert out.iloc[0].missing_eligibility_description
