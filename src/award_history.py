"""Layer 5 - historical-award check with USAspending.gov (objective, no AI).

For every grant's assistance listings (ALNs, e.g. 93.917), ask USAspending who
actually received grant awards under those listings in FY2022-FY2025:

  * did NC DHHS receive any?             (recipient name match, NC recipients)
  * did state agencies receive a real share?
  * or did the money go mainly to universities, tribes, local governments,
    or nonprofits/hospitals/companies?

This answers "is this a program state agencies like DHHS actually win". It is
NOT ground truth for strategic fit, and an ALN covers every NOFO under it, not
only this one.

Recipients are classified by NAME RULES (below), not USAspending's recipient-type
tags, which are incomplete: for ALN 93.917 NC DHHS received $187.6M by name but
only $91.2M is tagged as state government. Names the rules cannot place are
reported as `unclassified`; only the top recipients are fetched, so each result
carries a `coverage` share and is marked `unclear` when coverage is too low.

Every API response is cached in data/cache/usaspending/, so reruns are offline.

Usage:
    python src/award_history.py            # all grants Layer 2 triaged (needed for the L2 comparison)
    python src/award_history.py --offline  # cache only; fail on anything not cached
"""

import argparse
import hashlib
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests

import config

API = "https://api.usaspending.gov/api/v2"
CACHE = config.CACHE / "usaspending"
OUT_GRANTS = config.RESULTS / "award_history.csv"
OUT_ALNS = config.RESULTS / "award_history_alns.csv"
REPORT = config.RESULTS / "award_history_report.md"
ALN_RE = re.compile(r"^\d{2}\.\d{3}$")

STATES = ["ALABAMA", "ALASKA", "ARIZONA", "ARKANSAS", "CALIFORNIA", "COLORADO", "CONNECTICUT", "DELAWARE",
          "FLORIDA", "GEORGIA", "HAWAII", "IDAHO", "ILLINOIS", "INDIANA", "IOWA", "KANSAS", "KENTUCKY",
          "LOUISIANA", "MAINE", "MARYLAND", "MASSACHUSETTS", "MICHIGAN", "MINNESOTA", "MISSISSIPPI", "MISSOURI",
          "MONTANA", "NEBRASKA", "NEVADA", "NEW HAMPSHIRE", "NEW JERSEY", "NEW MEXICO", "NEW YORK",
          "NORTH CAROLINA", "NORTH DAKOTA", "OHIO", "OKLAHOMA", "OREGON", "PENNSYLVANIA", "RHODE ISLAND",
          "SOUTH CAROLINA", "SOUTH DAKOTA", "TENNESSEE", "TEXAS", "UTAH", "VERMONT", "VIRGINIA", "WASHINGTON",
          "WEST VIRGINIA", "WISCONSIN", "WYOMING", "DISTRICT OF COLUMBIA", "PUERTO RICO", "GUAM",
          "VIRGIN ISLANDS", "AMERICAN SAMOA", "NORTHERN MARIANA"]
_STATE_NAME = re.compile(r"\b(" + "|".join(STATES) + r")\b")
_UNIVERSITY = re.compile(r"UNIVERSITY|\bUNIV\b|COLLEGE|INSTITUTE OF TECHNOLOGY|POLYTECHNIC|REGENTS|BOARD OF TRUSTEES|"
                         r"SCHOOL OF MEDICINE|MEDICAL SCHOOL|HEALTH SCIENCE CENTER|RESEARCH FOUNDATION")
_TRIBAL = re.compile(r"\bTRIBES?\b|\bTRIBAL\b|PUEBLO|RANCHERIA|\bBAND OF\b|\bNATION\b|INDIAN|NATIVE VILLAGE|"
                     r"ALASKA NATIVE|NATIVE AMERICAN|NATIVE HAWAIIAN")
_LOCAL = re.compile(r"\bCOUNTY\b|\bCITY\b|\bTOWN( OF)?\b|VILLAGE OF|BOROUGH|PARISH|MUNICIPAL|SCHOOL DISTRICT|"
                    r"PUBLIC SCHOOLS|\bDISTRICT HEALTH\b")
_GOV_WORD = re.compile(r"DEPARTMENT|\bDEPT\b|DIVISION|OFFICE OF|AGENCY|EXECUTIVE|BUREAU|COMMISSION|AUTHORITY|"
                       r"ADMINISTRATION|CABINET|SECRETARY|GOVERNOR|STATE OF|COMMONWEALTH|\bSTATE\b")
_NOT_REAL = re.compile(r"MULTIPLE RECIPIENTS|REDACTED|MISCELLANEOUS|^$")
NC_DHHS = re.compile(r"NORTH CAROLINA DEP(ARTMEN)?T\.? OF HEALTH|HEALTH (AND|&) HUMAN SERVICES,? NORTH CAROLINA|"
                     r"\bN\.?C\.? DEP(ARTMEN)?T\.? OF HEALTH")
CLASSES = ["state_agency", "university", "tribal", "local_government", "nonprofit_or_other", "unclassified"]


def classify(name: str) -> str:
    """Deterministic recipient class from the recipient name. Order matters."""
    n = re.sub(r"\s+", " ", str(name or "").upper()).strip()
    if _NOT_REAL.search(n):
        return "unclassified"
    if _UNIVERSITY.search(n):
        return "university"
    if _TRIBAL.search(n):
        return "tribal"
    if _LOCAL.search(n):
        return "local_government"
    if (_STATE_NAME.search(n) or "STATE OF" in n or "COMMONWEALTH" in n) and _GOV_WORD.search(n):
        return "state_agency"
    return "nonprofit_or_other"


def parse_alns(listings) -> list[str]:
    if not isinstance(listings, str):
        return []
    return sorted({x.split("|")[0].strip() for x in listings.split(";") if x.strip()})


# ── Cached API access ───────────────────────────────────────────────────────

class Client:
    def __init__(self, offline: bool = False):
        self.offline = offline
        CACHE.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()

    def post(self, endpoint: str, payload: dict) -> dict:
        key = hashlib.sha256(json.dumps({"e": endpoint, "p": payload}, sort_keys=True).encode()).hexdigest()[:24]
        path = CACHE / f"{key}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))["response"]
        if self.offline:
            raise RuntimeError(f"not cached (offline): {endpoint} {payload.get('filters', {}).get('program_numbers')}")
        for attempt in range(5):
            try:
                r = self.session.post(f"{API}{endpoint}", json=payload, timeout=90)
            except requests.RequestException:
                time.sleep(2 ** attempt)
                continue
            if r.status_code == 200:
                data = r.json()
                path.write_text(json.dumps({"endpoint": endpoint, "payload": payload, "response": data}),
                                encoding="utf-8")
                return data
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"HTTP {r.status_code} {endpoint}: {r.text[:150]}")
        raise RuntimeError(f"USAspending unreachable after retries: {endpoint}")


def aln_history(client: Client, aln: str, cfg: dict) -> dict:
    """Award history for one assistance listing."""
    filters = {"program_numbers": [aln], "award_type_codes": cfg["award_type_codes"],
               "time_period": [{"start_date": cfg["start_date"], "end_date": cfg["end_date"]}]}
    out = {"aln": aln, "total": 0.0, **{c: 0.0 for c in CLASSES}, "nc_dhhs": 0.0, "nc_state_agency": 0.0,
           "nc_state_agency_names": "", "top_recipients": "", "error": ""}
    if not ALN_RE.match(aln):
        out["error"] = "not a standard assistance listing number"
        return out
    try:
        sot = client.post("/search/spending_over_time/", {"group": "fiscal_year", "filters": filters})
        out["total"] = float(sum(x["aggregated_amount"] or 0 for x in sot["results"]))
        if out["total"] <= 0:
            return out
        recips = []
        for page in range(1, cfg["national_recipient_pages"] + 1):
            res = client.post("/search/spending_by_category/recipient/",
                              {"filters": filters, "limit": 100, "page": page})
            recips += res.get("results", [])
            if not res.get("page_metadata", {}).get("hasNext"):
                break
        for r in recips:
            out[classify(r.get("name"))] += float(r.get("amount") or 0)
        out["top_recipients"] = "; ".join(f"{r.get('name')} (${(r.get('amount') or 0) / 1e6:.1f}M)" for r in recips[:3])
        nc = client.post("/search/spending_by_category/recipient/",
                         {"filters": {**filters, "recipient_locations": [{"country": "USA", "state": "NC"}]},
                          "limit": 100, "page": 1})
        nc_state = []
        for r in nc.get("results", []):
            name, amt = str(r.get("name") or ""), float(r.get("amount") or 0)
            if NC_DHHS.search(name.upper()):
                out["nc_dhhs"] += amt
            if classify(name) == "state_agency":
                out["nc_state_agency"] += amt
                nc_state.append(name)
        out["nc_state_agency_names"] = "; ".join(sorted(set(nc_state)))
    except RuntimeError as e:
        out["error"] = str(e)[:200]
    return out


# ── Per-grant verdicts ──────────────────────────────────────────────────────

def verdict(row: pd.Series, cfg: dict) -> str:
    if row["error"] and row["total"] == 0:
        return "unknown (API error or non-standard listing)"
    if row["total"] <= 0:
        return f"no awards found {cfg['fiscal_years_label']}"
    if row["nc_dhhs"] >= cfg["nc_dhhs_min_usd"]:
        return "NC DHHS has received awards"
    share = lambda c: row[c] / row["total"]
    if share("state_agency") >= cfg["state_agency_share_threshold"]:
        return "other state agencies win this"
    classified = sum(row[c] for c in CLASSES if c != "unclassified") / row["total"]
    if classified < cfg["min_classified_coverage"]:
        return "unclear (top recipients cover too little of the money)"
    for c, label in (("university", "mostly universities"), ("tribal", "mostly tribal / Native organizations"),
                     ("local_government", "mostly local governments"),
                     ("nonprofit_or_other", "mostly nonprofits, hospitals or companies")):
        if share(c) >= cfg["majority_share"]:
            return label
    return "mixed recipients" + (" (some state agencies)" if row["state_agency"] > 0 else " (no state agencies)")


def grant_history(grants: pd.DataFrame, alns: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    by_aln = alns.set_index("aln")
    rows = []
    for g in grants.itertuples():
        codes = [a for a in g.alns if a in by_aln.index]
        sub = by_aln.loc[codes] if codes else by_aln.iloc[0:0]
        rec = {"grant_id": g.grant_id, "opportunity_title": g.opportunity_title, "alns": ";".join(g.alns),
               **{k: float(sub[k].sum()) if len(sub) else 0.0
                  for k in ["total", *CLASSES, "nc_dhhs", "nc_state_agency"]},
               "nc_state_agency_names": "; ".join(sorted({n for s in sub["nc_state_agency_names"] for n in s.split("; ") if n})),
               "top_recipients": " | ".join(s for s in sub["top_recipients"] if s)[:400],
               "error": "; ".join(sorted({e for e in sub["error"] if e}))[:200] if len(sub) else "no assistance listing"}
        rec["state_agency_share"] = rec["state_agency"] / rec["total"] if rec["total"] else 0.0
        rec["university_share"] = rec["university"] / rec["total"] if rec["total"] else 0.0
        rec["coverage"] = sum(rec[c] for c in CLASSES if c != "unclassified") / rec["total"] if rec["total"] else 0.0
        rec["verdict"] = verdict(pd.Series(rec), cfg)
        rec["state_agency_history"] = (rec["nc_dhhs"] >= cfg["nc_dhhs_min_usd"]
                                       or rec["state_agency_share"] >= cfg["state_agency_share_threshold"])
        rows.append(rec)
    return pd.DataFrame(rows)


# ── Report ──────────────────────────────────────────────────────────────────

def _m(x) -> str:
    return f"${x / 1e6:,.1f}M" if abs(x) >= 1e6 else f"${x / 1e3:,.0f}K"


def _pct(x) -> str:
    # De-obligations (negative amounts) can push a share slightly outside 0-100%.
    return f"{max(0.0, min(1.0, x)) + 0.0:.0%}"


def _broad(alns: str) -> str:
    n = len([a for a in str(alns).split(";") if a])
    return f" (spans {n} listings)" if n > 3 else ""


def report(hist: pd.DataFrame, cfg: dict) -> list[str]:
    jev = pd.read_csv(config.RESULTS / "jev_outputs.csv")[["grant_id", "route", "domain_relevance", "applicant_role"]]
    deep = pd.read_csv(config.RESULTS / "deep_analysis.csv")
    h = hist.merge(jev, on="grant_id", how="left")
    fy = cfg["fiscal_years_label"]
    L = ["# Historical-award check (USAspending.gov)", "",
         f"Objective, non-AI check: who actually received grant awards under each grant's assistance listings in "
         f"**{fy}** (USAspending.gov, award types: block, formula and project grants, cooperative agreements). "
         "It answers *\"is this a program state agencies like DHHS actually win?\"*. It does **not** measure "
         "strategic fit, and an assistance listing covers every funding notice under it, not only this one.", "",
         "**How recipients are classified:** by name rules in `src/award_history.py` (state agency / university / "
         "tribal / local government / nonprofit-hospital-company), because USAspending's own recipient-type tags are "
         "incomplete (for listing 93.917, NC DHHS received $187.6M by name but only $91.2M is tagged as state "
         "government). Only the top 200 recipients per listing are fetched; `coverage` is the share of dollars those "
         "cover. 'State agency history' = NC DHHS received at least "
         f"{_m(cfg['nc_dhhs_min_usd'])}, or state agencies received at least "
         f"{cfg['state_agency_share_threshold']:.0%} of the dollars.", "",
         f"Grants checked: **{len(h)}** (every grant Jev triaged). Distinct assistance listings queried: "
         f"**{h['alns'].str.split(';').explode().replace('', pd.NA).dropna().nunique()}**.", ""]

    def show(df, title):
        rows = [f"### {title}", "", "| # | Grant | Verdict | NC DHHS | State-agency share | University share | Coverage |",
                "|---|---|---|---|---|---|---|"]
        for i, r in enumerate(df.itertuples(), 1):
            rows.append(f"| {i} | {r.opportunity_title[:70]} | {r.verdict}{_broad(r.alns)} | "
                        f"{_m(r.nc_dhhs) if r.nc_dhhs > 0 else '—'} | "
                        f"{_pct(r.state_agency_share)} | {_pct(r.university_share)} | {_pct(r.coverage)} |")
        n = len(df)
        rows += ["", f"**{int((df['nc_dhhs'] >= cfg['nc_dhhs_min_usd']).sum())} of {n}** have awards to NC DHHS "
                     f"(at least {_m(cfg['nc_dhhs_min_usd'])} in {fy}); "
                     f"**{int(df['state_agency_history'].sum())} of {n}** have NC DHHS or substantial state-agency "
                     f"awards; {int(df['verdict'].str.startswith('no awards').sum())} have no awards in {fy}; "
                     f"{int(df['verdict'].str.startswith(('unknown', 'unclear')).sum())} unknown/unclear.", ""]
        return rows

    top_open = pd.read_csv(config.RESULTS / "ranked_grants.csv").head(10)[["grant_id"]]
    top_watch = pd.read_csv(config.RESULTS / "watchlist.csv").head(5)[["grant_id"]]
    L += show(top_open.merge(h, on="grant_id"), "Top 10 open grants")
    L += show(top_watch.merge(h, on="grant_id"), "Top 5 watchlist grants")

    dep = h[h["route"] == "deprioritized"]
    dr = h[h["route"] == "deep_review"]
    fn = dep[dep["state_agency_history"]]
    uni_only = dr[(dr["verdict"] == "mostly universities") & (dr["state_agency"] == 0) & (dr["nc_dhhs"] == 0)]
    L += ["## Compared with Layer 2 (Jev) routing", "",
          f"- **Deprioritized by Jev:** {len(dep)}. Of these, **{len(fn)}** have a history of awards to NC DHHS or "
          f"substantial state-agency awards (possible false negatives). "
          f"{int((dep['nc_dhhs'] >= cfg['nc_dhhs_min_usd']).sum())} of them under a listing where NC DHHS itself received awards.",
          f"- **Sent to deep review:** {len(dr)}. Of these, **{len(uni_only)}** went mostly to universities with no "
          f"state-agency recipients among the top 200 (probably research-type programs).",
          f"- Grants Jev deprioritized vs sent on, share with state-agency history: "
          f"{dep['state_agency_history'].mean():.0%} vs {dr['state_agency_history'].mean():.0%}.", ""]
    if len(fn):
        L += ["### Deprioritized grants with state-agency award history (inspect each)", "",
              "| Grant | Jev relevance / role | Verdict | NC DHHS | State share |", "|---|---|---|---|---|"]
        for r in fn.sort_values(["nc_dhhs", "state_agency_share"], ascending=False).head(25).itertuples():
            L.append(f"| {r.opportunity_title[:90]} | {r.domain_relevance} / {r.applicant_role} | {r.verdict}{_broad(r.alns)} | "
                     f"{_m(r.nc_dhhs) if r.nc_dhhs > 0 else '—'} | {_pct(r.state_agency_share)} |")
        L += ["", "_Caveat: an assistance listing is shared by many funding notices. A listing states win (e.g. a "
                  "broad CDC or HRSA listing) can still carry a specific notice meant for others, such as a "
                  "tribal-only or university-only competition. Treat these as leads to check, not proven misses. "
                  "Our inspection of each is in `docs/failure_modes.md` (F9)._", ""]
    L += ["## Verdicts across all checked grants", "",
          h["verdict"].value_counts().rename("grants").to_frame().to_markdown(), ""]
    return L


def run(offline: bool = False, workers: int = 6) -> pd.DataFrame:
    agency = config.load_agency()
    cfg = agency["layer5_award_history"]
    feats = pd.read_csv(config.LAYER1_OUTPUT, dtype=str, keep_default_na=False)
    jev = pd.read_csv(config.RESULTS / "jev_outputs.csv", dtype=str)
    grants = feats[feats["grant_id"].isin(jev["grant_id"])].copy()
    grants["alns"] = grants["opportunity_assistance_listings"].map(parse_alns)
    codes = sorted({a for l in grants["alns"] for a in l})
    client = Client(offline=offline)
    print(f"Award history: {len(grants)} grants, {len(codes)} assistance listings "
          f"({cfg['fiscal_years_label']}, cache: {CACHE})")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        alns = pd.DataFrame(list(pool.map(lambda a: aln_history(client, a, cfg), codes)))
    alns.to_csv(OUT_ALNS, index=False)
    errs = alns[alns["error"] != ""]
    if len(errs):
        print(f"  {len(errs)} listings could not be answered: {errs['error'].str[:60].value_counts().to_dict()}")
    hist = grant_history(grants, alns, cfg)
    hist.to_csv(OUT_GRANTS, index=False)
    lines = report(hist, cfg)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:4]))
    print(f"Wrote {OUT_GRANTS}, {OUT_ALNS}, {REPORT}")
    return hist


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--offline", action="store_true", help="use cached responses only")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    run(offline=a.offline, workers=a.workers)
