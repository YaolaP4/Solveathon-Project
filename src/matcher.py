"""Scoring and ranking: a transparent, blended 0-100 score with a breakdown for every opportunity.

Signals (each 0-1, weights from agency/priorities.json -> "matchmaker"):

  semantic     45%  similarity between the opportunity text and each of the plan's 20 objectives
                    (Azure OpenAI embeddings; TF-IDF if Azure OpenAI is unavailable). The best
                    objective becomes the "matched goal".
  keyword      25%  profile keywords found in the title (counts double) and description.
  eligibility  15%  can a state agency apply? Structured applicant types + the eligibility text.
  timing       10%  enough time to apply. Forecasts get a "watch" flag instead of a deadline.
  affinity      5%  has NC DHHS (or other state agencies) actually won awards under this
                    assistance listing? USAspending.gov, FY2022-FY2025 (qualifier Layer 5).

Confidence band from the total: High / Medium / Low (thresholds in the config). Two tracks are
kept apart from the main shortlist, as in the qualifier: research mechanisms (NIH R01 etc.,
for a university partner) and records whose eligibility text excludes state agencies.
"""

import hashlib
import re
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

import aoai
from award_history import CLASSES, Client, aln_history, parse_alns, verdict

DEFAULT = {
    "weights": {"semantic": 0.45, "keyword": 0.25, "eligibility": 0.15, "timing": 0.10, "affinity": 0.05},
    "calibration": {"embedding_margin": [-0.10, 0.20], "tfidf": [0.02, 0.22]},
    "off_topic_anchors": [
        "Basic scientific research in physics, astronomy, chemistry, mathematics, engineering or geosciences, led by universities and research institutes.",
        "Defense, military, Navy, Army, Air Force and national security research, technology development and procurement.",
        "Arts, humanities, museums, libraries, archives and cultural heritage projects.",
        "International development, foreign assistance, diplomacy, embassy public diplomacy and international exchange programs abroad.",
        "Agriculture, farming, forestry, fisheries, wildlife, public lands, parks and natural resource conservation.",
        "Energy, transportation, highways, transit, aviation, broadband construction, manufacturing and semiconductor industry.",
        "Environmental science, climate, oceans, water resources and ecosystem research.",
        "Small business innovation research, technology commercialization and economic development for businesses.",
        "Higher education, STEM education, graduate fellowships and postdoctoral research training.",
        "Biomedical laboratory research on disease mechanisms, genetics, molecular biology and clinical trials at research institutions.",
    ],
    "keyword_full_credit_hits": 4,
    "bands": {"high": 55, "medium": 45},
    "aln_lookup_top_n": 250,
}

SIGNAL_LABELS = {"semantic": "Plan alignment (semantic)", "keyword": "Keyword / program fit",
                 "eligibility": "Eligibility (state agency)", "timing": "Time to apply", "affinity": "Funder history"}


def mm_settings(agency: dict) -> dict:
    cfg = {**DEFAULT, **{k: v for k, v in (agency.get("matchmaker") or {}).items() if not k.startswith("_")}}
    cfg["weights"] = {**DEFAULT["weights"], **cfg.get("weights", {})}
    # "Unrelated fields" depend on the agency: environment is off-topic for health, and the reverse.
    anchors = (agency.get("profile") or {}).get("off_topic_anchors")
    if anchors:
        cfg["off_topic_anchors"] = anchors
    return cfg


def agency_short(agency: dict) -> str:
    return agency.get("agency_short") or agency["profile"]["agency_id"].upper()


# ── Plan documents ──────────────────────────────────────────────────────────

def objective_docs(agency: dict) -> list[dict]:
    priorities = {p["id"]: p["text"] for p in agency.get("department_priorities") or []}
    docs = []
    for g in agency["strategic_priorities"]:
        for o in g["objectives"]:
            text = f"{g['name']}: {g['description']} Objective: {o['text']}"
            if o.get("related_priority") in priorities:      # the plan's priority area this objective serves
                text += f" Department priority: {priorities[o['related_priority']]}"
            docs.append({"goal_id": g["id"], "goal_name": g["name"], "objective_id": o["id"], "objective": o["text"],
                         "source": o.get("source", ""), "text": text})
    return docs


def opportunity_text(r: pd.Series) -> str:
    return f"{r['opportunity_title']}\n{r['summary_text']}\n{r['applicant_eligibility_description']}"[:6000]


def _h(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:20]


# ── Semantic similarity ─────────────────────────────────────────────────────

def embed_cached(store, texts: list[str], log=print) -> np.ndarray:
    """Embeddings for texts, reusing cache/embeddings/{deployment}-{dims}.* in storage."""
    tag = f"{aoai.embed_deployment()}-{aoai.EMBED_DIMENSIONS}"
    keys = store.read_json(f"cache/embeddings/{tag}.json", default=[]) or []
    vecs = store.read_npy(f"cache/embeddings/{tag}.npy")
    if vecs is None or len(vecs) != len(keys):
        keys, vecs = [], np.zeros((0, aoai.EMBED_DIMENSIONS), dtype=np.float32)
    pos = {k: i for i, k in enumerate(keys)}
    hashes = [_h(t) for t in texts]
    missing, seen = [], set()
    for i, h in enumerate(hashes):        # identical texts (re-posted listings) are embedded once
        if h not in pos and h not in seen:
            seen.add(h)
            missing.append(i)
    if missing:
        log(f"  embeddings: {len(texts) - len(missing)} cached or repeated, {len(missing)} new")
        new = np.asarray(aoai.embed([texts[i] for i in missing]), dtype=np.float32)
        for i in missing:
            pos[hashes[i]] = len(keys)
            keys.append(hashes[i])
        vecs = np.vstack([vecs, new]) if len(vecs) else new
        assert len(vecs) == len(keys), "embedding cache out of step"
        store.write_npy(f"cache/embeddings/{tag}.npy", vecs)
        store.write_json(f"cache/embeddings/{tag}.json", keys)
    out = vecs[[pos[h] for h in hashes]]
    return out / np.clip(np.linalg.norm(out, axis=1, keepdims=True), 1e-9, None)


def _lin(x, lo_hi):
    lo, hi = lo_hi
    return np.clip((x - lo) / (hi - lo), 0, 1)


def tfidf_similarity(opp_texts: list[str], plan: list[str]) -> np.ndarray:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True).fit(opp_texts + plan)
    return cosine_similarity(vec.transform(opp_texts), vec.transform(plan))


def similarity(store, opp_texts: list[str], docs: list[dict], cfg: dict, log=print) -> tuple[np.ndarray, str, dict]:
    """(n_opps x n_objectives) plan-alignment matrix in 0-1, the method used, and raw parts for the breakdown.

    hybrid (default): the average of
      * meaning-based: embedding similarity to the objective MINUS the best similarity to a set of
        off-topic domains (defence, arts, physics, ...). Raw similarity alone ranked long generic
        announcements (a Navy research BAA, a National Park Service agreement) near the top;
        the margin asks "closer to the DHHS plan than to unrelated fields?";
      * word-based: TF-IDF similarity to the objective.
    Tuned on the 1,037 live opportunities the qualifier's pipeline had already reviewed: AUC 0.91 and 76%
    of the top 50 on topic, vs 0.84 / 54% for raw embeddings and 0.81 / 50% for TF-IDF alone
    (src/tune_semantic.py, docs/tuning_report.md).
    tfidf (fallback if Azure OpenAI is unavailable): the word-based part alone.
    """
    plan = [d["text"] for d in docs]
    tf = tfidf_similarity(opp_texts, plan)
    tf_part = _lin(tf, cfg["calibration"]["tfidf"])
    if aoai.available():
        try:
            o = embed_cached(store, opp_texts, log)
            p = embed_cached(store, plan, log)
            a = embed_cached(store, cfg["off_topic_anchors"], log)
            sim = o @ p.T
            off = (o @ a.T)
            margin = sim - off.max(axis=1, keepdims=True)
            emb_part = _lin(margin, cfg["calibration"]["embedding_margin"])
            anchor_names = [s.split(",")[0] for s in cfg["off_topic_anchors"]]
            parts = {"embedding": sim, "off_topic": off.max(axis=1), "off_topic_name": [anchor_names[i] for i in off.argmax(axis=1)],
                     "tfidf": tf}
            return 0.5 * emb_part + 0.5 * tf_part, "hybrid", parts
        except Exception as e:  # graceful degradation: the demo still works without Azure OpenAI
            log(f"  WARNING embeddings failed ({str(e)[:120]}); falling back to TF-IDF")
    return tf_part, "tfidf", {"tfidf": tf}


# ── Other signals ───────────────────────────────────────────────────────────

def keyword_patterns(keywords: list[str]) -> dict[str, re.Pattern]:
    return {k: re.compile(r"(?<![A-Za-z0-9])" + re.escape(k) + r"(?![A-Za-z0-9])", re.I) for k in keywords}


def keyword_hits(title: str, body: str, pats: dict) -> tuple[list[str], list[str]]:
    in_title = [k for k, p in pats.items() if p.search(title or "")]
    in_body = [k for k, p in pats.items() if k not in in_title and p.search(body or "")]
    return in_title, in_body


def eligibility_signal(r: pd.Series) -> tuple[float, str]:
    if r["text_higher_ed_only"] or r["text_tribal_only"] or r["text_individuals_only"]:
        return 0.0, "eligibility text limits applicants to universities, tribes or individuals"
    if r["state_government_listed"]:
        return 1.0, "state governments are listed as eligible"
    if r["text_mentions_state_agency"]:
        return 0.9, "eligibility text mentions state agencies"
    if r["unrestricted_listed"]:
        return 0.8, "eligibility is unrestricted"
    if r["other_listed"] or r["applicant_types_blank"]:
        return 0.4, "eligibility unclear ('other' or not stated); read the announcement"
    return 0.0, "state governments are not listed as eligible"


def timing_signal(r: pd.Series) -> tuple[float, str]:
    if r["is_forecast"]:
        if r["forecast_close_passed"]:
            return 0.3, "forecast looks out of date: its estimated close date has passed"
        return 0.7, "forecast: not open yet, time to prepare"
    if r["rolling_deadline"]:
        return (0.6, "rolling, but first come first served") if r["rolling_funds_limited"] else (0.8, "applications accepted anytime")
    if pd.isna(r["days_until_close"]):
        return 0.5, "no close date stated"
    d = int(r["days_until_close"])
    return float(r["deadline_score"]) / 10, f"closes in {d} day{'s' if d != 1 else ''}"


def aln_record(client, aln: str, cfg: dict) -> dict:
    """Award history for one assistance listing (qualifier Layer 5), plus every North Carolina recipient
    and amount, so any agency's own awards can be found by its name pattern."""
    res = aln_history(client, aln, cfg)
    res["nc_recipients"] = []
    if res.get("total", 0) > 0 and not res.get("error"):
        filters = {"program_numbers": [aln], "award_type_codes": cfg["award_type_codes"],
                   "time_period": [{"start_date": cfg["start_date"], "end_date": cfg["end_date"]}],
                   "recipient_locations": [{"country": "USA", "state": "NC"}]}
        try:   # same request aln_history just made, so it comes from the response cache
            nc = client.post("/search/spending_by_category/recipient/", {"filters": filters, "limit": 100, "page": 1})
            res["nc_recipients"] = [{"name": str(r.get("name") or ""), "amount": float(r.get("amount") or 0)}
                                    for r in nc.get("results", [])]
        except RuntimeError as e:
            res["error"] = str(e)[:200]
    return res


def aln_affinity(store, alns_per_row: list[list[str]], agency: dict, log=print) -> dict[str, dict]:
    """Award history per assistance listing, cached in storage and shared by every agency."""
    cfg = agency["layer5_award_history"]
    cache = store.read_json("cache/aln_history.json", default={}) or {}
    codes = sorted({a for row in alns_per_row for a in row})
    todo = [a for a in codes if a not in cache or "nc_recipients" not in cache[a]]
    if todo:
        log(f"  funder history: {len(codes) - len(todo)} listings cached, {len(todo)} to look up on USAspending.gov")
        client = Client(offline=False)
        with ThreadPoolExecutor(6) as pool:
            for res in pool.map(lambda a: aln_record(client, a, cfg), todo):
                if not res.get("error") or res.get("total", 0) > 0:
                    cache[res["aln"]] = res
        store.write_json("cache/aln_history.json", cache)
    return cache


def affinity_signal(alns: list[str], hist: dict, cfg: dict, related_funder: bool, agency: dict) -> tuple[float, str, dict]:
    short = agency_short(agency)
    pattern = re.compile((agency.get("profile") or {}).get("usaspending_recipient_pattern") or r"$^")
    rows = [hist[a] for a in alns if a in hist]
    if not rows:
        if related_funder:
            return 0.5, "a federal department that often funds this kind of agency; award history not looked up", {}
        return 0.3, "award history not looked up", {}
    agg = {k: sum(float(r.get(k) or 0) for r in rows) for k in ["total", *CLASSES, "nc_state_agency"]}
    agency_usd = sum(x["amount"] for r in rows for x in r.get("nc_recipients", []) if pattern.search(x["name"].upper()))
    agg["nc_dhhs"] = agency_usd            # verdict() calls this field "NC DHHS"; it is this agency's own awards
    agg["error"] = ""
    v = verdict(pd.Series(agg), cfg).replace("NC DHHS", short)
    share = agg["state_agency"] / agg["total"] if agg["total"] else 0
    summary = {"verdict": v, "agency_usd": agency_usd, "agency": short, "total_usd": agg["total"],
               "state_agency_share": round(share, 3),
               "top_recipients": " | ".join(r.get("top_recipients", "") for r in rows if r.get("top_recipients"))[:300]}
    if agency_usd >= cfg["nc_dhhs_min_usd"]:
        return 1.0, f"{short} received ${agency_usd / 1e6:,.1f}M under this listing ({cfg['fiscal_years_label']})", summary
    if share >= cfg["state_agency_share_threshold"]:
        return 0.7, f"other state agencies receive {share:.0%} of this listing's awards", summary
    if agg["total"] <= 0:
        return 0.3, f"no awards found {cfg['fiscal_years_label']}", summary
    return 0.1, f"awards go {v.replace('mostly ', 'mostly to ')}", summary


# ── Score everything ────────────────────────────────────────────────────────

def score(live: pd.DataFrame, agency: dict, store, log=print) -> tuple[pd.DataFrame, dict]:
    cfg = mm_settings(agency)
    w = cfg["weights"]
    docs = objective_docs(agency)
    texts = [opportunity_text(r) for _, r in live.iterrows()]
    sim, method, parts = similarity(store, texts, docs, cfg, log)
    best = sim.argmax(axis=1)
    sem = sim.max(axis=1)
    rows = np.arange(len(best))

    pats = keyword_patterns(agency["profile"]["keywords"])
    out = live.copy()
    out["semantic_method"] = method
    out["s_semantic"] = sem.round(4)
    out["semantic_tfidf"] = parts["tfidf"][rows, best].round(4)
    if "embedding" in parts:
        out["semantic_embedding"] = parts["embedding"][rows, best].round(4)
        out["semantic_off_topic"] = parts["off_topic"].round(4)
        out["semantic_off_topic_name"] = parts["off_topic_name"]
    out["matched_objective_id"] = [docs[i]["objective_id"] for i in best]
    out["matched_goal_id"] = [docs[i]["goal_id"] for i in best]
    # Second-best goal (different goal), shown so staff can see near-ties.
    goal_ids = sorted({d["goal_id"] for d in docs})
    per_goal = np.stack([sim[:, [j for j, d in enumerate(docs) if d["goal_id"] == g]].max(axis=1) for g in goal_ids], axis=1)
    out["goal_similarities"] = [dict(zip(goal_ids, map(lambda x: round(float(x), 4), row))) for row in per_goal]

    kw = [keyword_hits(r["opportunity_title"], r["summary_text"], pats) for _, r in live.iterrows()]
    out["keywords_in_title"] = [k[0] for k in kw]
    out["keywords_in_text"] = [k[1] for k in kw]
    out["s_keyword"] = [min(1.0, (2 * len(t) + len(b)) / cfg["keyword_full_credit_hits"]) for t, b in kw]

    el = [eligibility_signal(r) for _, r in live.iterrows()]
    out["s_eligibility"], out["eligibility_reason"] = [e[0] for e in el], [e[1] for e in el]
    tm = [timing_signal(r) for _, r in live.iterrows()]
    out["s_timing"], out["timing_reason"] = [t[0] for t in tm], [t[1] for t in tm]

    # Pre-score without funder history, then look up award history only for the top candidates.
    pre = (w["semantic"] * out["s_semantic"] + w["keyword"] * out["s_keyword"]
           + w["eligibility"] * out["s_eligibility"] + w["timing"] * out["s_timing"])
    out["alns"] = out["opportunity_assistance_listings"].map(parse_alns)
    top = pre.sort_values(ascending=False).index[: cfg["aln_lookup_top_n"]]
    try:
        hist = aln_affinity(store, out.loc[top, "alns"].tolist(), agency, log)
    except Exception as e:
        log(f"  WARNING funder history unavailable ({str(e)[:120]})")
        hist = {}
    acfg = agency["layer5_award_history"]
    related = set((agency.get("profile") or {}).get("related_federal_agencies") or [])
    af = [affinity_signal(r["alns"], hist, acfg, r["top_level_agency_name"] in related, agency) for _, r in out.iterrows()]
    out["s_affinity"], out["affinity_reason"] = [a[0] for a in af], [a[1] for a in af]
    out["award_history"] = [a[2] for a in af]

    total = 100 * (pre + w["affinity"] * out["s_affinity"])
    out["score"] = total.round(1)
    b = cfg["bands"]
    out["confidence"] = np.select([out["score"] >= b["high"], out["score"] >= b["medium"]], ["High", "Medium"], "Low")
    out["track"] = np.select([out["research_mechanism"], out["s_eligibility"] == 0],
                             ["research", "not_eligible"], "agency")
    out = out.sort_values("score", ascending=False, kind="stable").reset_index(drop=True)
    out["rank"] = out.groupby("track").cumcount() + 1
    meta = {"method": method, "calibration": cfg["calibration"], "weights": w, "bands": b,
            "aln_listings_with_history": len(hist)}
    return out, meta


def semantic_reason(r: pd.Series) -> str:
    base = f"closest objective {r['matched_objective_id']}: word similarity {r['semantic_tfidf']:.2f}"
    if r["semantic_method"] == "hybrid":
        return (base + f", meaning similarity {r['semantic_embedding']:.2f} vs {r['semantic_off_topic']:.2f} to the "
                f"nearest unrelated field ({r['semantic_off_topic_name'].lower()})")
    return base + " (meaning-based part unavailable today)"


def breakdown(r: pd.Series, w: dict) -> list[dict]:
    reasons = {
        "semantic": semantic_reason(r),
        "keyword": ("title: " + ", ".join(r["keywords_in_title"]) if r["keywords_in_title"] else "")
                   + ("; " if r["keywords_in_title"] and r["keywords_in_text"] else "")
                   + ("text: " + ", ".join(r["keywords_in_text"][:8]) if r["keywords_in_text"] else "")
                   or "no profile keywords found",
        "eligibility": r["eligibility_reason"], "timing": r["timing_reason"], "affinity": r["affinity_reason"],
    }
    return [{"signal": k, "label": SIGNAL_LABELS[k], "value": round(float(r[f"s_{k}"]), 3), "weight": w[k],
             "points": round(100 * w[k] * float(r[f"s_{k}"]), 1), "max_points": round(100 * w[k], 1),
             "reason": reasons[k]} for k in w]
