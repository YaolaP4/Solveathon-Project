"""Evaluation: prove the matches are good (starter kit sec. 6), computed live from storage.

Labels    eval/labels.json  {"labels": [{"id", "labeler", "relevant": true|false|null, "note", "at"}]}
Sample    eval/sample.json  fixed once, so later labels stay comparable:
            our top 10 + the keyword baseline's top 10 + 5 from our ranks 11-100 + 5 random others
            (the agency track only: research grants and not-eligible records are separate lists).

Baseline  "keyword-only monitoring": rank by how many profile keywords appear in the title and
          description (title hits first). No semantics, no eligibility, no timing, no history.
          Also recorded: which records Grants.gov's own keyword search returns for each profile
          keyword (eval/keyword_baseline/latest.json).

Metrics   precision@10 (ours vs baseline), recall@25 on the labeled set, relevant items we rank in
          the top 25 that the baseline does not, labeler agreement (count and Cohen's kappa),
          and decisions vs scores (the feedback loop).
"""

import hashlib
import random

SAMPLE_PATH = "eval/sample.json"
LABELS_PATH = "eval/labels.json"


def baseline_order(records: list[dict]) -> list[dict]:
    """Keyword-only ranking of the agency-track records."""
    def key(r):
        return (-len(r.get("keywords_matched") or []), -len(r.get("keywords_in_title") or []), r["title"])
    return sorted(records, key=key)


def agency_records(doc: dict) -> list[dict]:
    return [r for r in doc["records"] if r["track"] == "agency"]


def draw_sample(doc: dict, seed: int = 42) -> dict:
    recs = agency_records(doc)
    ours = recs[:10]
    base = baseline_order(recs)[:10]
    chosen, items = set(), []

    def add(r, stratum):
        if r["id"] not in chosen:
            chosen.add(r["id"])
            # A snapshot of what the labeler sees, so an item stays labelable after it closes.
            snap = {k: r.get(k) for k in ("number", "agency", "status", "close_date", "eligibility", "url")}
            snap["description"] = (r.get("description") or "")[:1500]
            snap["eligibility_text"] = (r.get("eligibility_text") or "")[:1500]
            items.append({"id": r["id"], "stratum": stratum, "title": r["title"], "snapshot": snap})

    for r in ours:
        add(r, "our top 10")
    for r in base:
        add(r, "keyword baseline top 10")
    rng = random.Random(seed)
    middle = [r for r in recs[10:100] if r["id"] not in chosen]
    for r in rng.sample(middle, min(5, len(middle))):
        add(r, "our ranks 11-100")
    rest = [r for r in recs[100:] if r["id"] not in chosen]
    for r in rng.sample(rest, min(5, len(rest))):
        add(r, "random from the rest")
    return {"drawn_from_run": doc["run_id"], "as_of": doc["as_of"], "seed": seed, "items": items}


def labeler_order(sample: dict, labeler: str) -> list[dict]:
    """Same items for everyone, shuffled per labeler so nobody sees them in rank order."""
    items = list(sample["items"])
    seed = int(hashlib.sha1(labeler.strip().lower().encode()).hexdigest()[:8], 16)
    random.Random(seed).shuffle(items)
    return items


def _latest_labels(labels: list[dict]) -> dict[tuple[str, str], dict]:
    out = {}
    for l in labels:
        out[(l["id"], l["labeler"].strip().lower())] = l
    return out


def resolved(labels: list[dict]) -> dict[str, dict]:
    """Per item: votes, majority label (ties and 'unsure' -> None), and whether labelers disagree."""
    by_item: dict[str, list[dict]] = {}
    for (iid, _), l in _latest_labels(labels).items():
        by_item.setdefault(iid, []).append(l)
    out = {}
    for iid, ls in by_item.items():
        yes = sum(1 for l in ls if l["relevant"] is True)
        no = sum(1 for l in ls if l["relevant"] is False)
        out[iid] = {"votes": ls, "yes": yes, "no": no,
                    "label": True if yes > no else False if no > yes else None,
                    "disagree": yes > 0 and no > 0}
    return out


def cohen_kappa(pairs: list[tuple[bool, bool]]) -> float | None:
    if len(pairs) < 2:
        return None
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    pa = sum(a for a, _ in pairs) / n
    pb = sum(b for _, b in pairs) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return None if pe == 1 else round((po - pe) / (1 - pe), 2)


def precision_at(order: list[dict], res: dict, k: int) -> dict:
    top = order[:k]
    judged = [r for r in top if res.get(r["id"], {}).get("label") is not None]
    rel = [r for r in judged if res[r["id"]]["label"]]
    return {"k": k, "judged": len(judged), "relevant": len(rel),
            "precision": round(len(rel) / len(judged), 2) if judged else None}


def metrics(doc: dict, sample: dict | None, labels: list[dict], decisions: dict, keyword_hits: dict | None) -> dict:
    recs = agency_records(doc)
    rank = {r["id"]: i + 1 for i, r in enumerate(recs)}
    base = baseline_order(recs)
    brank = {r["id"]: i + 1 for i, r in enumerate(base)}
    res = resolved(labels)

    # Agreement for ONE fixed pair of labelers (the two who labeled most), so rater A and rater B are the
    # same people on every item, as Cohen's kappa assumes. Disagreements are listed for any labelers.
    labelers = sorted({l["labeler"].strip() for l in labels})
    counts = {}
    for (iid, who), l in _latest_labels(labels).items():
        if l["relevant"] is not None:
            counts[who] = counts.get(who, 0) + 1
    pair = sorted(sorted(counts, key=lambda w: (-counts[w], w))[:2])
    pairs, disagreements = [], []
    for iid, v in res.items():
        yn = [l for l in v["votes"] if l["relevant"] is not None]
        by = {l["labeler"].strip().lower(): bool(l["relevant"]) for l in yn}
        if len(pair) == 2 and all(p in by for p in pair):
            pairs.append((by[pair[0]], by[pair[1]]))
        if v["disagree"]:
            disagreements.append({"id": iid, "votes": [{"labeler": l["labeler"], "relevant": l["relevant"],
                                                         "note": l.get("note", "")} for l in yn]})
    names = {l["labeler"].strip().lower(): l["labeler"].strip() for l in labels}
    relevant_ids = [i for i, v in res.items() if v["label"] is True and i in rank]
    in25 = [i for i in relevant_ids if rank[i] <= 25]
    base25 = [i for i in relevant_ids if brank.get(i, 10 ** 9) <= 25]
    found_not_baseline = [i for i in in25 if brank.get(i, 10 ** 9) > 25]

    # Grants.gov keyword search coverage of our High/Medium matches.
    kw_missed = None
    if keyword_hits:
        found = {i for ids in keyword_hits.values() for i in ids}
        strong = [r for r in recs if r["confidence"] in ("High", "Medium")]
        kw_missed = {"strong_matches": len(strong),
                     "missed_by_every_keyword_search": [r["id"] for r in strong if r["id"] not in found],
                     "keywords": len(keyword_hits), "ids_returned": len(found)}

    # Feedback loop: decisions vs scores.
    by_id = {r["id"]: r for r in doc["records"]}
    fb = {"Pursue": [], "Maybe": [], "Pass": []}
    for iid, hist in (decisions or {}).items():
        if hist and iid in by_id:
            d = hist[-1]
            fb.setdefault(d["decision"], []).append({"id": iid, "score": by_id[iid]["score"],
                                                     "confidence": by_id[iid]["confidence"], "title": by_id[iid]["title"]})
    feedback = {k: {"n": len(v), "mean_score": round(sum(x["score"] for x in v) / len(v), 1) if v else None} for k, v in fb.items()}
    feedback["pass_on_high"] = [x for x in fb.get("Pass", []) if x["confidence"] == "High"]
    feedback["pursue_on_low"] = [x for x in fb.get("Pursue", []) if x["confidence"] == "Low"]

    return {
        "sample_size": len(sample["items"]) if sample else 0, "labelers": labelers,
        "labeled_items": sum(1 for v in res.values() if v["label"] is not None),
        "relevant_items": len(relevant_ids),
        "ours_p10": precision_at(recs, res, 10), "baseline_p10": precision_at(base, res, 10),
        "recall25": {"relevant": len(relevant_ids), "ours_in_top25": len(in25), "baseline_in_top25": len(base25),
                     "ours": round(len(in25) / len(relevant_ids), 2) if relevant_ids else None,
                     "baseline": round(len(base25) / len(relevant_ids), 2) if relevant_ids else None},
        "found_not_baseline": found_not_baseline,
        "agreement": {"pairs": len(pairs), "agree": sum(a == b for a, b in pairs), "kappa": cohen_kappa(pairs),
                      "labelers": [names.get(p, p) for p in pair]},
        "disagreements": disagreements, "keyword_search": kw_missed, "feedback": feedback,
        "ours_rank": rank, "baseline_rank": brank, "resolved": res,
    }
