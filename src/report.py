"""Final deliverable: the top-results list for a non-technical reader.

Reads Layer 4's ranked_grants.csv and watchlist.csv and writes
data/results/top_results.md and top_results.csv - rank, grant, score, deadline,
award, owning division, matched goal, one-line rationale, main risk, and the
evidence status of the eligibility claim.

Usage:
    python src/report.py [--top 10] [--watch 5] [--mock]
"""

import argparse

import pandas as pd

import config
import scoring


def _money(v) -> str:
    if pd.isna(v):
        return "not stated"
    return f"${v / 1e6:.1f}M" if v >= 1e6 else f"${v / 1e3:.0f}K"


def _truthy(v) -> bool:
    return str(v).strip().lower() == "true"


def build(ranked: pd.DataFrame, agency: dict, n: int, forecast: bool) -> pd.DataFrame:
    goals = {p["id"]: p["name"] for p in agency["strategic_priorities"]}
    divisions = {d["id"]: d["name"] for d in agency["divisions"]}
    live = ranked[ranked["score_status"] != "confirmed_ineligible"].head(n)
    rows = []
    for r in live.itertuples():
        if forecast:
            when = f"forecast close {r.forecasted_close_date}" if pd.notna(r.forecasted_close_date) else "forecast, no date"
            if _truthy(getattr(r, "forecast_check_now", False)):
                when += " (forecast post date passed - may already be open, check Grants.gov now)"
            if _truthy(getattr(r, "forecast_close_passed", False)):
                when += " (date passed - check if posted)"
        elif pd.notna(r.close_date_real):
            when = f"{str(r.close_date_real)[:10]} ({int(r.days_until_close)} days)"
        else:
            when = "rolling" if _truthy(getattr(r, "rolling_deadline", False)) else "not stated"
        evidence = "verified quote" if _truthy(r.eligibility_quote_verified) else "UNVERIFIED - check eligibility"
        rows.append({
            "rank": r.rank, "grant": r.opportunity_title, "score": r.final_score, "deadline": when,
            "award (est.)": _money(r.award_value_usd),
            "owner": divisions.get(r.owning_division, r.owning_division),
            "goal": goals.get(r.matched_goal, r.matched_goal),
            "why": r.one_line_rationale, "main risk": r.major_risk,
            "DHHS role": f"{r.applicant_role_verified} ({evidence})",
            "cost share": r.requires_cost_share, "link": r.url,
        })
    return pd.DataFrame(rows)


def run(top: int = 10, watch: int = 5, mock: bool = False) -> None:
    agency = config.load_agency()
    out_dir = config.MOCK_RESULTS if mock else config.RESULTS
    open_list = build(pd.read_csv(out_dir / "ranked_grants.csv"), agency, top, forecast=False)
    watch_list = build(pd.read_csv(out_dir / "watchlist.csv"), agency, watch, forecast=True)
    pd.concat([open_list.assign(list="apply now"), watch_list.assign(list="watchlist")]).to_csv(
        out_dir / "top_results.csv", index=False)

    weights, *_ = scoring.scoring_config(agency)
    formula = ", ".join(f"{k.replace('_score', '').replace('_', ' ')} {v:.0%}" for k, v in weights.items())
    md = [f"# Top federal grant opportunities for {agency['agency_short']}",
          f"_As of {agency['as_of_date']}. Scores are 0-100 from a fixed, published formula ({formula})._",
          "" if not mock else "\n**MOCK RUN - fake model answers, do not use.**\n",
          f"## Apply now: top {len(open_list)} open opportunities", ""]
    for r in open_list.to_dict("records"):
        md += [f"### {r['rank']}. {r['grant']} — {r['score']:.0f}/100",
               f"- **Why:** {r['why']}",
               f"- **Owner:** {r['owner']} · **Goal:** {r['goal']} · **DHHS role:** {r['DHHS role']}",
               f"- **Deadline:** {r['deadline']} · **Award:** {r['award (est.)']} · **Cost share:** {r['cost share']}",
               f"- **Main risk:** {r['main risk']}", f"- [Grant listing]({r['link']})", ""]
    md += [f"## Watchlist: {len(watch_list)} forecasted opportunities to prepare for", ""]
    for r in watch_list.to_dict("records"):
        md += [f"- **{r['grant']}** ({r['score']:.0f}/100) — {r['why']} Owner: {r['owner']}. "
               f"{r['deadline']}. [Listing]({r['link']})"]
    (out_dir / "top_results.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"Wrote {out_dir / 'top_results.md'} and top_results.csv")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--watch", type=int, default=5)
    ap.add_argument("--mock", action="store_true")
    a = ap.parse_args()
    run(a.top, a.watch, a.mock)
