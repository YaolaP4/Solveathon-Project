"""Layer 5 - validation. Human labels decide whether the pipeline works.

Three steps:

1. python src/validation.py sample
   Draws a STRATIFIED sample of grants that reach Layer 2 and writes a blind
   labeling sheet: data/validation/labels.csv. Strata come from the keyword
   baseline (not from Jev), so the sample does not depend on the model being
   evaluated and can be labeled before any API run. Rows are shuffled and the
   sheet shows no model output or stratum. Two teammates label every row.

2. python src/validation.py spotcheck      (after the real pipeline run)
   Writes data/validation/spotcheck.csv: the top 10 open grants, the top 5
   watchlist grants, 5 random grants ranked 50+, and 5 random grants Layer 2
   deprioritized - to check each against our criteria by hand.

3. python src/validation.py evaluate
   Reads the labels and the pipeline outputs and writes
   data/results/validation_report.md: labeler agreement, Layer 2 recall and
   precision with stratified-bootstrap confidence intervals, the keyword
   baseline at the same review budget, every false negative, and a summary of
   the AI error log.

Label meaning ("relevant"): the DHHS grants coordinator should spend time on
this grant - DHHS could plausibly lead or be a named partner AND it advances a
DHHS strategic goal. Deadline and award size are NOT part of the label.
"""

import argparse
import json
import sys

import numpy as np
import pandas as pd

import config
from keyword_baseline import OUTPUT as BASELINE
from text_utils import strip_html, truncate

VAL = config.DATA / "validation"
LABELS = VAL / "labels.csv"
DESIGN = VAL / "sample_design.csv"
SPOTCHECK = VAL / "spotcheck.csv"
REPORT = config.RESULTS / "validation_report.md"
SEED = 42
# Stratum -> (baseline rank range, sample size)
STRATA = {"S1_top100": (1, 100, 30), "S2_rank101_400": (101, 400, 30), "S3_rank401_plus": (401, 10**9, 30)}
LABEL_COLUMNS = ["labeler_A_relevant", "labeler_A_role", "labeler_B_relevant", "labeler_B_role",
                 "final_relevant", "notes"]
YES, NO = {"y", "yes", "1", "true"}, {"n", "no", "0", "false"}


# ── 1. Sampling ─────────────────────────────────────────────────────────────

def draw_sample(features: pd.DataFrame, baseline: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    live = features[~features["hard_filtered"].astype(bool)].merge(
        baseline[["grant_id", "baseline_rank"]], on="grant_id")
    live["baseline_rank"] = live["baseline_rank"].astype(int)
    rng = np.random.default_rng(SEED)
    picks, design = [], []
    for name, (lo, hi, n) in STRATA.items():
        pool = live[live["baseline_rank"].between(lo, hi)]
        take = pool.iloc[rng.choice(len(pool), size=min(n, len(pool)), replace=False)]
        picks.append(take.assign(stratum=name))
        design.append({"stratum": name, "baseline_rank_from": lo, "baseline_rank_to": min(hi, len(live)),
                       "population_size": len(pool), "sample_size": len(take)})
    sample = pd.concat(picks).sample(frac=1, random_state=SEED).reset_index(drop=True)
    sample.insert(0, "sample_id", [f"V{i + 1:03d}" for i in range(len(sample))])
    return sample, pd.DataFrame(design)


def write_sheet(sample: pd.DataFrame) -> pd.DataFrame:
    sheet = pd.DataFrame({
        "sample_id": sample["sample_id"],
        "grant_id": sample["grant_id"],
        "title": sample["opportunity_title"],
        "federal_agency": sample["agency_name"],
        "applicant_types": sample["applicant_types"].fillna("").str.replace(";", ", "),
        "eligibility_text": sample["applicant_eligibility_description"].fillna("").map(lambda t: truncate(strip_html(t), 1500)),
        "summary": sample["summary_description"].fillna("").map(lambda t: truncate(strip_html(t), 2000)),
        "url": sample["url"],
    })
    for c in LABEL_COLUMNS:
        sheet[c] = ""
    return sheet


def cmd_sample(force: bool) -> None:
    if LABELS.exists() and not force:
        existing = pd.read_csv(LABELS, dtype=str).fillna("")
        if (existing[[c for c in LABEL_COLUMNS if c in existing]] != "").any().any():
            sys.exit(f"{LABELS} already has labels in it. Refusing to overwrite human work "
                     f"(use --force only if you really mean to).")
    features = pd.read_csv(config.LAYER1_OUTPUT)
    if not BASELINE.exists():
        import keyword_baseline
        keyword_baseline.run()
    sample, design = draw_sample(features, pd.read_csv(BASELINE))
    VAL.mkdir(parents=True, exist_ok=True)
    write_sheet(sample).to_csv(LABELS, index=False)
    sample[["sample_id", "grant_id", "stratum"]].merge(design, on="stratum").to_csv(DESIGN, index=False)
    print(design.to_string(index=False))
    print(f"\nWrote blind labeling sheet {LABELS} ({len(sample)} grants).")
    print("Fill labeler_A_relevant / labeler_B_relevant with Y or N (and optionally the role: "
          "lead/partner/atypical/ineligible). Label independently; do not look at model output first.")


# ── 2. Spot-check sheet ─────────────────────────────────────────────────────

def cmd_spotcheck() -> None:
    ranked = pd.read_csv(config.RESULTS / "ranked_grants.csv")
    watch = pd.read_csv(config.RESULTS / "watchlist.csv")
    jev = pd.read_csv(config.RESULTS / "jev_outputs.csv")
    rng = np.random.default_rng(SEED)
    low = ranked[ranked["rank"] >= 50]
    depri = jev[jev["route"] == "deprioritized"]
    parts = [ranked.head(10).assign(group="top10_open"), watch.head(5).assign(group="top5_watchlist"),
             low.iloc[rng.choice(len(low), size=min(5, len(low)), replace=False)].assign(group="random_rank50plus"),
             depri.iloc[rng.choice(len(depri), size=min(5, len(depri)), replace=False)].assign(group="random_deprioritized")]
    cols = ["group", "rank", "grant_id", "opportunity_title", "final_score", "one_line_rationale"]
    sheet = pd.concat([p.reindex(columns=cols) for p in parts])
    for c in ["check_eligible", "check_aligned", "check_deadline_realistic", "check_award_worth_it",
              "verdict_should_be_here", "notes"]:
        sheet[c] = ""
    VAL.mkdir(parents=True, exist_ok=True)
    sheet.to_csv(SPOTCHECK, index=False)
    print(f"Wrote {SPOTCHECK} ({len(sheet)} rows). Fill the check_* columns Y/N against our 5 criteria.")


# ── 3. Evaluation ───────────────────────────────────────────────────────────

def _yn(v) -> float:
    v = str(v).strip().lower()
    return 1.0 if v in YES else 0.0 if v in NO else np.nan


def resolve_labels(labels: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    a, b, final = (labels[c].map(_yn) for c in ("labeler_A_relevant", "labeler_B_relevant", "final_relevant"))
    resolved = final.where(final.notna(), a.where(a == b))
    labels = labels.assign(label_A=a, label_B=b, relevant=resolved)
    unresolved = labels.loc[a.notna() & b.notna() & (a != b) & final.isna(), "sample_id"].tolist()
    return labels, unresolved


def cohen_kappa(a: pd.Series, b: pd.Series) -> float:
    m = a.notna() & b.notna()
    a, b = a[m], b[m]
    if len(a) == 0:
        return float("nan")
    po = (a == b).mean()
    pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
    return float("nan") if pe == 1 else (po - pe) / (1 - pe)


def weighted_rates(df: pd.DataFrame, retained_col: str) -> dict:
    """Design-weighted recall and precision. Each labeled grant stands for
    population_size / labeled_in_stratum grants of its stratum."""
    w = df["population_size"] / df.groupby("stratum")["relevant"].transform("count")
    rel, ret = df["relevant"] == 1, df[retained_col].astype(bool)
    tp = (w * (rel & ret)).sum()
    recall = tp / (w * rel).sum() if (w * rel).sum() else np.nan
    precision = tp / (w * ret).sum() if (w * ret).sum() else np.nan
    return {"recall": recall, "precision": precision}


def bootstrap_ci(df: pd.DataFrame, retained_col: str, reps: int = 2000) -> dict:
    rng = np.random.default_rng(SEED)
    groups = [g for _, g in df.groupby("stratum")]
    draws = {"recall": [], "precision": []}
    for _ in range(reps):
        boot = pd.concat([g.iloc[rng.integers(0, len(g), len(g))] for g in groups])
        r = weighted_rates(boot, retained_col)
        for k in draws:
            if not np.isnan(r[k]):
                draws[k].append(r[k])
    return {k: (np.percentile(v, 2.5), np.percentile(v, 97.5)) if v else (np.nan, np.nan)
            for k, v in draws.items()}


def fmt(x) -> str:
    return "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{100 * x:.0f}%"


def cmd_evaluate() -> None:
    labels, unresolved = resolve_labels(pd.read_csv(LABELS, dtype=str).fillna(""))
    if unresolved:
        print(f"WARNING: labelers disagree on {len(unresolved)} grants with no final_relevant: "
              f"{', '.join(unresolved)}. They are excluded until adjudicated.")
    design = pd.read_csv(DESIGN)
    df = labels.merge(design[["sample_id", "stratum", "population_size"]], on="sample_id")
    df = df[df["relevant"].notna()].copy()
    if df.empty:
        sys.exit("No resolved labels yet - fill in labels.csv first.")

    lines = ["# Validation report", "",
             f"Labeled and resolved: **{len(df)}** grants "
             f"({len(unresolved)} awaiting adjudication). Label = 'the coordinator should spend time on this'.", ""]
    kappa = cohen_kappa(labels["label_A"], labels["label_B"])
    both = labels["label_A"].notna() & labels["label_B"].notna()
    agree = (labels.loc[both, "label_A"] == labels.loc[both, "label_B"]).mean() if both.any() else np.nan
    lines += ["## Do humans agree?", "",
              f"- Double-labeled: {int(both.sum())}; raw agreement {fmt(agree)}; Cohen's kappa **{kappa:.2f}**"
              if both.any() else "- No double-labeled grants yet.",
              "- Disagreements show how ambiguous 'relevant' is; they cap how well any method can score.", ""]
    lines += ["## Labeled sample by stratum", "",
              df.groupby("stratum").agg(labeled=("relevant", "size"), relevant=("relevant", "sum"),
                                        population=("population_size", "first")).astype(int).to_markdown(), ""]

    jev_path = config.RESULTS / "jev_outputs.csv"
    if jev_path.exists():
        jev = pd.read_csv(jev_path)[["grant_id", "route", "domain_relevance", "domain_relevance_p",
                                      "applicant_role", "route_reason"]]
        df = df.merge(jev, on="grant_id", how="left")
        missing = df["route"].isna().sum()
        df["jev_retained"] = df["route"].fillna("deep_review").eq("deep_review")
        rates, ci = weighted_rates(df, "jev_retained"), bootstrap_ci(df, "jev_retained")
        n_retained = int(pd.read_csv(jev_path)["route"].eq("deep_review").sum())

        base = pd.read_csv(BASELINE)[["grant_id", "baseline_rank"]]
        df = df.merge(base, on="grant_id", how="left")
        df["baseline_retained"] = df["baseline_rank"].astype(float) <= n_retained
        brates, bci = weighted_rates(df, "baseline_retained"), bootstrap_ci(df, "baseline_retained")

        lines += ["## Layer 2 (Jev) vs keyword baseline", "",
                  f"Jev sends **{n_retained}** grants to deep review. The baseline is given the same budget "
                  f"(its top {n_retained} by TF-IDF similarity). Recall = share of relevant grants that reach Layer 3. "
                  "Estimates are weighted by stratum size; intervals are 95% stratified bootstrap.", "",
                  "| Method | Recall | 95% CI | Precision | 95% CI |", "|---|---|---|---|---|",
                  f"| Jev routing | **{fmt(rates['recall'])}** | {fmt(ci['recall'][0])}–{fmt(ci['recall'][1])} "
                  f"| {fmt(rates['precision'])} | {fmt(ci['precision'][0])}–{fmt(ci['precision'][1])} |",
                  f"| Keyword baseline (same budget) | {fmt(brates['recall'])} | {fmt(bci['recall'][0])}–{fmt(bci['recall'][1])} "
                  f"| {fmt(brates['precision'])} | {fmt(bci['precision'][0])}–{fmt(bci['precision'][1])} |", ""]
        if missing:
            lines += [f"_{missing} labeled grants had no Jev output (API error?) and were counted as retained._", ""]
        fn = df[(df["relevant"] == 1) & ~df["jev_retained"]]
        lines += ["## Layer 2 false negatives (relevant but deprioritized) - inspect every one", ""]
        lines += ([f"- `{r.sample_id}` {r.title} — Jev: {r.domain_relevance} (p={r.domain_relevance_p}), "
                   f"role {r.applicant_role}; {r.route_reason}" for r in fn.itertuples()] or ["- None in the sample."])
        lines += [""]
    else:
        lines += ["## Layer 2", "", "_No jev_outputs.csv yet - run the pipeline, then re-run evaluate._", ""]

    deep_path = config.RESULTS / "deep_analysis.csv"
    if deep_path.exists():
        deep = pd.read_csv(deep_path)
        deep = deep[deep["status"] == "ok"][["grant_id", "recommended_for_review", "strategic_alignment"]]
        d = df.merge(deep, on="grant_id")
        if len(d):
            rec = d["recommended_for_review"].astype(str).str.lower().eq("true")
            agree3 = (rec == (d["relevant"] == 1)).mean()
            lines += ["## Layer 3 recommendation vs human label", "",
                      f"- {len(d)} labeled grants were deep-analyzed; `recommended_for_review` matches the human label "
                      f"on {fmt(agree3)} (unweighted).",
                      f"- Recommended but labeled not relevant: {int((rec & (d['relevant'] == 0)).sum())}; "
                      f"labeled relevant but not recommended: {int((~rec & (d['relevant'] == 1)).sum())}.", ""]

    err_path = config.RESULTS / "ai_error_log.csv"
    if err_path.exists():
        err = pd.read_csv(err_path)
        err = err[err["check"] != "over_layer3_cap"]
        lines += ["## Where the AI was wrong (automatic checks, `ai_error_log.csv`)", ""]
        if len(err):
            lines += [err.groupby(["check", "severity"]).size().rename("count").reset_index().to_markdown(index=False), "",
                      "Examples:", ""]
            lines += [f"- **{r.check}** — {r.opportunity_title}: {r.detail}"
                      for r in err[err["severity"] == "high"].head(5).itertuples()]
        else:
            lines += ["- No problems logged."]
        lines += [""]

    config.RESULTS.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nWrote {REPORT}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample")
    s.add_argument("--force", action="store_true")
    sub.add_parser("spotcheck")
    sub.add_parser("evaluate")
    a = ap.parse_args()
    {"sample": lambda: cmd_sample(a.force), "spotcheck": cmd_spotcheck, "evaluate": cmd_evaluate}[a.cmd]()
