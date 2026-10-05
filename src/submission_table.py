"""Submission item 1: the top-results table, one row per grant, rationale tied to our criteria.

Writes submission/top_results.csv (opens in any spreadsheet) and submission/top_results.md.
Rows: the top 10 open grants and the top 5 watchlist grants. Each row has the model's
one-line rationale plus a criteria check built deterministically from the five criteria
(agency/agency_profile.md), and the USAspending award history for NC DHHS.

Usage:  python src/submission_table.py
"""

import pandas as pd

import config

OUT = config.ROOT / "submission"
ROLE_TEXT = {"lead": "DHHS can lead", "partner": "DHHS as partner", "atypical": "eligible but atypical",
             "unclear": "eligibility unclear", "ineligible": "ineligible"}


def _money(v) -> str:
    if pd.isna(v) or v <= 0:
        return "not stated"
    return f"${v / 1e6:.1f}M" if v >= 1e6 else f"${v / 1e3:.0f}K"


def _true(v) -> bool:
    return str(v).strip().lower() == "true"


def rows(ranked: pd.DataFrame, hist: pd.DataFrame, agency: dict, n: int, track: str) -> list[dict]:
    goals = {p["id"]: p["name"] for p in agency["strategic_priorities"]}
    divs = {d["id"]: d["name"] for d in agency["divisions"]}
    nc_min = agency["layer5_award_history"]["nc_dhhs_min_usd"]
    h = hist.set_index("grant_id")
    out = []
    for r in ranked[ranked["score_status"] != "confirmed_ineligible"].head(n).itertuples():
        if track == "watchlist":
            deadline = f"forecast close {r.forecasted_close_date}" if pd.notna(r.forecasted_close_date) else "forecast, no date"
            if _true(getattr(r, "forecast_check_now", False)):
                deadline += " - may already be open, check Grants.gov now"
            elif _true(getattr(r, "forecast_close_passed", False)):
                deadline += " - date passed, check if posted"
        elif pd.notna(r.close_date_real):
            deadline = f"{str(r.close_date_real)[:10]} ({int(r.days_until_close)} days)"
        else:
            deadline = "rolling" if _true(getattr(r, "rolling_deadline", False)) else "not stated"
        role = r.applicant_role_verified
        evidence = "quote verified" if _true(r.eligibility_quote_verified) else "quote NOT verified"
        criteria = (f"1 Eligibility: {ROLE_TEXT.get(role, role)} ({evidence}) | "
                    f"2 Goal: {goals.get(r.matched_goal, 'none matched')} ({r.strategic_alignment:.0f}/10) | "
                    f"3 Owner: {divs.get(r.owning_division, r.owning_division)} (fit {r.operational_fit:.0f}/10) | "
                    f"4 Timing: {deadline} | 5 Award: {_money(r.award_value_usd)}, cost share {r.requires_cost_share}")
        nc = h.loc[r.grant_id, "nc_dhhs"] if r.grant_id in h.index else 0.0
        out.append({
            "list": "Apply now" if track == "open" else "Prepare now (forecast)",
            "rank": int(r.rank), "grant": r.opportunity_title, "score_0_100": round(float(r.final_score)),
            "one_line_rationale": r.one_line_rationale, "criteria_check": criteria,
            "main_risk": r.major_risk,
            "nc_dhhs_awards_fy22_25": _money(nc) if nc >= nc_min else "none on record",
            "past_recipients": h.loc[r.grant_id, "verdict"] if r.grant_id in h.index else "",
            "link": r.url,
        })
    return out


def run() -> pd.DataFrame:
    agency = config.load_agency()
    hist = pd.read_csv(config.RESULTS / "award_history.csv")
    table = pd.DataFrame(rows(pd.read_csv(config.RESULTS / "ranked_grants.csv"), hist, agency, 10, "open")
                         + rows(pd.read_csv(config.RESULTS / "watchlist.csv"), hist, agency, 5, "watchlist"))
    OUT.mkdir(exist_ok=True)
    table.to_csv(OUT / "top_results.csv", index=False, encoding="utf-8-sig")  # BOM: Excel shows dashes right

    md = [f"# Top federal grant opportunities for {agency['agency_name']}", "",
          f"As of {agency['as_of_date']} (data pulled 2026-08-18). Score: 0–100 from a published formula "
          "(strategic fit 30%, ability to run it 25%, award size 15%, deadline 15%, eligibility 15%). "
          "NC DHHS award history: USAspending.gov, FY2022–FY2025. The criteria check numbers match our five "
          "criteria in `agency/agency_profile.md`.", ""]
    for name in ["Apply now", "Prepare now (forecast)"]:
        md += [f"## {name}", "", "| # | Grant | Score | Why (one line) | NC DHHS won FY22–25 |", "|---|---|---|---|---|"]
        for r in table[table["list"] == name].itertuples():
            md.append(f"| {r.rank} | [{r.grant}]({r.link}) | {r.score_0_100} | {r.one_line_rationale} | {r.nc_dhhs_awards_fy22_25} |")
        md += [""]
    md += ["## Criteria check and main risk, per grant", ""]
    for r in table.itertuples():
        md += [f"**{r.list} #{r.rank}: {r.grant}**", f"- Criteria: {r.criteria_check}",
               f"- Main risk: {r.main_risk}", f"- Past recipients under this program: {r.past_recipients}", ""]
    (OUT / "top_results.md").write_text("\n".join(md), encoding="utf-8")
    print(f"Wrote {OUT / 'top_results.csv'} and {OUT / 'top_results.md'} ({len(table)} grants)")
    return table


if __name__ == "__main__":
    run()
