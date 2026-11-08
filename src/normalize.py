"""Normalize Grants.gov API records into one consistent schema (data contract, docs/data_contract.md).

The qualifier pipeline read a Grants.gov CSV export. The daily job reads the live API instead,
so this module maps each API record onto the same columns the export had. That lets the
daily job reuse the qualifier's tested rules unchanged:

    clean_data.clean()               parse dates/numbers/booleans, plain-text helpers
    deterministic.build_features()   deadlines, award size, cost share, eligibility signals,
                                     research mechanisms, administrative notices, hard filters

Then: de-duplicate by opportunity number, drop closed / archived / administrative records, and
FLAG (never silently drop) records that are missing key fields.
"""

import html
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import config
from clean_data import clean
from deterministic import build_features, settings

# Grants.gov eligibility codes -> the applicant-type slugs used by the CSV export (and Layer 1).
APPLICANT_SLUGS = {
    "00": "state_governments", "01": "county_governments", "02": "city_or_township_governments",
    "04": "special_district_governments", "05": "independent_school_districts",
    "06": "public_and_state_institutions_of_higher_education",
    "07": "federally_recognized_native_american_tribal_governments",
    "08": "public_and_indian_housing_authorities", "11": "other_native_american_tribal_organizations",
    "12": "nonprofits_non_higher_education_with_501c3", "13": "nonprofits_non_higher_education_without_501c3",
    "20": "private_institutions_of_higher_education", "21": "individuals",
    "22": "for_profit_organizations_other_than_small_businesses", "23": "small_businesses",
    "25": "other", "99": "unrestricted",
}
DETAIL_URL = "https://www.grants.gov/search-results-detail/{id}"


def _d(s) -> str:
    """'2027-02-11-00-00-00' -> '2027-02-11'; anything else -> ''."""
    s = str(s or "")
    return s[:10] if len(s) >= 10 and s[4] == "-" else ""


def _num(v) -> str:
    try:
        return "" if v in (None, "") else str(float(v))
    except (TypeError, ValueError):
        return ""


def api_to_row(hit: dict, detail: dict | None) -> dict:
    """One search hit (+ its fetchOpportunity detail) -> one row in the CSV-export schema."""
    d = detail or {}
    status = (hit.get("oppStatus") or "").strip().lower()
    is_forecast = status == "forecasted" or (d.get("docType") == "forecast" and not d.get("synopsis"))
    syn = d.get("forecast") if is_forecast else d.get("synopsis")
    syn = syn or d.get("synopsis") or d.get("forecast") or {}
    fc = d.get("forecast") or {}
    agency = syn.get("agencyDetails") or d.get("agencyDetails") or {}
    top = syn.get("topAgencyDetails") or d.get("topAgencyDetails") or {}
    alns = ";".join(f"{c.get('cfdaNumber', '')}|{c.get('programTitle', '')}" for c in d.get("cfdas") or [])
    if not alns:
        alns = ";".join(f"{c}|" for c in hit.get("cfdaList") or [])
    types = ";".join(APPLICANT_SLUGS.get(str(t.get("id")), f"code_{t.get('id')}") for t in syn.get("applicantTypes") or [])
    close = "" if is_forecast else _d(syn.get("responseDateStr"))
    if not close and not is_forecast and hit.get("closeDate"):
        try:
            close = datetime.strptime(hit["closeDate"], "%m/%d/%Y").strftime("%Y-%m-%d")
        except ValueError:
            close = ""
    return {
        "opportunity_id": str(hit.get("id") or d.get("id")),
        "opportunity_number": hit.get("number") or d.get("opportunityNumber") or "",
        "opportunity_title": html.unescape(hit.get("title") or d.get("opportunityTitle") or "").strip(),
        "opportunity_status": status,
        "agency_code": hit.get("agencyCode") or d.get("owningAgencyCode") or "",
        "category": ((d.get("opportunityCategory") or {}).get("description") or "").lower(),
        "post_date": _d(syn.get("postingDateStr")),
        "close_date": close,
        "close_date_description": syn.get("responseDateDesc") or "",
        "archive_date": _d(syn.get("archiveDateStr")),
        "is_cost_sharing": "" if syn.get("costSharing") is None else str(bool(syn.get("costSharing"))),
        "expected_number_of_awards": _num(syn.get("numberOfAwards")),
        "estimated_total_program_funding": _num(syn.get("estimatedFunding")),
        "award_floor": _num(syn.get("awardFloor")),
        "award_ceiling": _num(syn.get("awardCeiling")),
        "opportunity_assistance_listings": alns,
        "funding_instruments": ";".join(x.get("description", "") for x in syn.get("fundingInstruments") or []),
        "funding_categories": ";".join(x.get("description", "") for x in syn.get("fundingActivityCategories") or []),
        "applicant_types": types,
        "applicant_eligibility_description": syn.get("applicantEligibilityDesc") or "",
        "agency_name": agency.get("agencyName") or hit.get("agency") or "",
        "top_level_agency_name": top.get("agencyName") or "",
        "is_forecast": str(bool(is_forecast)),
        "forecasted_post_date": _d(fc.get("estSynopsisPostingDateStr")) if is_forecast else "",
        "forecasted_close_date": _d(fc.get("estApplicationResponseDateStr")) if is_forecast else "",
        "forecasted_award_date": _d(fc.get("estAwardDateStr")) if is_forecast else "",
        "forecasted_project_start_date": _d(fc.get("estProjectStartDateStr")) if is_forecast else "",
        "fiscal_year": str(fc.get("fiscalYear") or ""),
        "updated_at": _d(syn.get("createTimeStampStr")),
        "url": DETAIL_URL.format(id=hit.get("id")),
        "summary_description": (syn.get("forecastDesc") if is_forecast else syn.get("synopsisDesc")) or "",
        "has_detail": str(bool(detail)),
    }


def _iso(v) -> str:
    return "" if pd.isna(v) else pd.Timestamp(v).strftime("%Y-%m-%d")


def normalize(hits: list[dict], details: dict, today: str, agency: dict) -> tuple[pd.DataFrame, dict]:
    """API records -> (feature frame of live records, stats). Rows are opportunities still open or forecast."""
    rows = [api_to_row(h, details.get(h["id"])) for h in hits]
    raw = pd.DataFrame(rows).astype(str)
    cleaned, _ = clean(raw)
    cfg = settings(agency)
    cfg["as_of_date"] = today          # the daily job judges deadlines against today, not a fixed date
    cfg["data_pulled_date"] = today
    feats = build_features(cleaned, cfg)

    stats = {"records_in": len(feats)}
    # De-duplicate by opportunity number: keep the most recently updated record.
    feats["_upd"] = pd.to_datetime(feats["updated_at"], errors="coerce")
    feats = feats.sort_values(["opportunity_number", "_upd"], ascending=[True, False], kind="stable")
    dup = feats["opportunity_number"].ne("") & feats.duplicated("opportunity_number", keep="first")
    stats["duplicates_dropped"] = int(dup.sum())
    feats = feats[~dup].drop(columns="_upd")

    stats["dropped_closed_or_admin"] = int(feats["hard_filtered"].sum())
    stats["dropped_reasons"] = feats.loc[feats["hard_filtered"], "hard_filter_reason"].value_counts().to_dict()
    live = feats[~feats["hard_filtered"]].copy()

    # Data quality: flag, never drop.
    live["no_detail"] = live["has_detail"].astype(str).str.lower() != "true"
    live["no_close_date"] = ~live["is_forecast"] & live["close_date_real"].isna()
    problems = {
        "no detail record": live["no_detail"],
        "description under 100 characters": live["description_too_short"],
        "no eligibility information": live["applicant_types_blank"] & live["missing_eligibility_description"],
        "no close date": live["no_close_date"] & ~live["rolling_deadline"],
        "no award amount": live["missing_award_amount"],
    }
    live["quality_issues"] = [
        [name for name, mask in problems.items() if bool(mask.loc[i])] for i in live.index]
    live["low_quality"] = live["quality_issues"].map(lambda x: bool({"no detail record", "description under 100 characters",
                                                                       "no eligibility information"} & set(x)))
    stats["records_out"] = len(live)
    stats["low_quality"] = int(live["low_quality"].sum())
    stats["posted"] = int((~live["is_forecast"]).sum())
    stats["forecasted"] = int(live["is_forecast"].sum())
    return live.reset_index(drop=True), stats


def minimum_record(r: pd.Series, ingested_at: str) -> dict:
    """The minimum opportunity schema from the starter kit (sec. 5.0)."""
    close = r["close_date_real"] if not r["is_forecast"] else r.get("forecasted_close_date")
    days = r["days_until_close"] if not r["is_forecast"] else np.nan
    return {
        "id": r["grant_id"], "source": "grants.gov", "number": r["opportunity_number"],
        "title": r["opportunity_title"], "agency": r["agency_name"], "top_agency": r["top_level_agency_name"],
        "status": "forecasted" if r["is_forecast"] else "posted",
        "open_date": _iso(r["post_date"]) or _iso(r.get("forecasted_post_date")),
        "close_date": _iso(close) or ("rolling" if r["rolling_deadline"] else "no close date"),
        "days_to_close": None if pd.isna(days) else int(days),
        "eligibility": r["applicant_types"], "eligibility_text": r["applicant_eligibility_description"],
        "category": r["funding_categories"], "award_ceiling": None if pd.isna(r["award_ceiling"]) else float(r["award_ceiling"]),
        "award_floor": None if pd.isna(r["award_floor"]) else float(r["award_floor"]),
        "total_funding": None if pd.isna(r["estimated_total_program_funding"]) else float(r["estimated_total_program_funding"]),
        "expected_awards": None if pd.isna(r["expected_number_of_awards"]) else int(r["expected_number_of_awards"]),
        "cost_sharing": r["requires_cost_share"], "assistance_listings": r["opportunity_assistance_listings"],
        "funding_instruments": r["funding_instruments"],
        "description": r["summary_text"], "url": r["url"], "ingested_at": ingested_at,
        "low_quality": bool(r["low_quality"]), "quality_issues": list(r["quality_issues"]),
    }


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


__all__ = ["normalize", "minimum_record", "api_to_row", "now_iso", "config"]
