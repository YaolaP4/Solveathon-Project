"""Learn from staff decisions (bonus quest: "Learn From the Users").

Every daily run reads the agency's recorded decisions. For each opportunity on today's list, it finds the most
similar opportunity that staff already decided on (meaning-based similarity of the announcement text, the same
cached embeddings the matcher uses):

  * very similar to one staff PASSED   -> confidence lowered one step, with "similar to <title>, which staff passed"
  * very similar to one staff PURSUED  -> confidence raised one step, with "similar to <title>, which staff pursued"

The score never changes, and nothing is hidden: the adjustment and its reason are shown on the record, and
staff decide. This also catches re-posted versions of something staff already judged. The threshold is
conservative (cosine >= 0.90 between whole announcements) so only near-duplicates and close siblings move.

Without Azure OpenAI (no embeddings) the step is skipped.
"""

import numpy as np
import pandas as pd

import aoai
import matcher

THRESHOLD = 0.90
UP = {"Low": "Medium", "Medium": "High", "High": "High"}
DOWN = {"High": "Medium", "Medium": "Low", "Low": "Low"}


def latest_decisions(store, aid: str) -> dict[str, dict]:
    doc = store.read_json(f"decisions/{aid}.json", default={}) or {}
    return {oid: hist[-1] for oid, hist in (doc.get("decisions") or {}).items() if hist}


def apply(scored: pd.DataFrame, store, aid: str, log=print) -> tuple[pd.DataFrame, dict]:
    """Returns (scored with 'feedback_note' and adjusted confidence, stats)."""
    out = scored.copy()
    out["feedback_note"] = ""
    decided = {k: v for k, v in latest_decisions(store, aid).items() if v.get("decision") in ("Pursue", "Pass")}
    stats = {"decisions_used": len(decided), "raised": 0, "lowered": 0}
    if not decided or not aoai.available():
        return out, stats
    texts = [matcher.opportunity_text(r) for _, r in out.iterrows()]
    vecs = matcher.embed_cached(store, texts, log)          # cached by text: no new API calls in a normal run
    idx = {gid: i for i, gid in enumerate(out["grant_id"])}
    # Decisions on opportunities that are no longer listed cannot be used (their text is not in today's pull).
    anchors = [(gid, d) for gid, d in decided.items() if gid in idx]
    if not anchors:
        return out, stats
    A = vecs[[idx[g] for g, _ in anchors]]
    sim = vecs @ A.T
    titles = out["opportunity_title"].tolist()
    for i in range(len(out)):
        order = np.argsort(-sim[i])
        for j in order:
            gid, d = anchors[j]
            if gid == out.at[i, "grant_id"]:
                continue                                     # never compare a record with its own decision
            if sim[i, j] < THRESHOLD:
                break
            conf = out.at[i, "confidence"]
            if d["decision"] == "Pass":
                out.at[i, "confidence"] = DOWN[conf]
                verb, stats["lowered"] = "passed", stats["lowered"] + (DOWN[conf] != conf)
            else:
                out.at[i, "confidence"] = UP[conf]
                verb, stats["raised"] = "pursued", stats["raised"] + (UP[conf] != conf)
            out.at[i, "feedback_note"] = (f"similar to “{titles[idx[gid]][:90]}”, which staff {verb}"
                                          f" (confidence {conf} → {out.at[i, 'confidence']})")
            break
    log(f"  learning from {len(anchors)} staff decisions: {stats['raised']} raised, {stats['lowered']} lowered")
    return out, stats
