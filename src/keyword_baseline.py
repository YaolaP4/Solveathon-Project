"""Layer 5 - keyword (TF-IDF) baseline. A comparison, not a pipeline feature.

Ranks every grant by lexical similarity to the agency's strategic plan
(mission, the 20 objectives, and the division scopes in priorities.json).
Each objective/division is its own document and a grant's score is its best
match, so a grant only has to fit one priority well.

validation.py compares this ranking against Jev's routing on the human-labeled
sample. If Jev does not beat it, the AI layer is not earning its place.

Output: data/results/keyword_baseline.csv
Usage:  python src/keyword_baseline.py
"""

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import config

OUTPUT = config.RESULTS / "keyword_baseline.csv"


def plan_documents(agency: dict) -> dict[str, str]:
    docs = {}
    for p in agency["strategic_priorities"]:
        for o in p["objectives"]:
            docs[o["id"]] = f"{p['name']}. {p['description']} {o['text']}"
    for d in agency["divisions"]:
        docs[f"div:{d['id']}"] = f"{d['name']}. {d['scope']}"
    docs["mission"] = agency["mission"]
    return docs


def score(grants: pd.DataFrame, agency: dict) -> pd.DataFrame:
    docs = plan_documents(agency)
    texts = grants["grant_text"].fillna("").tolist()
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True, min_df=1)
    vec.fit(texts + list(docs.values()))
    sim = cosine_similarity(vec.transform(texts), vec.transform(list(docs.values())))
    keys = list(docs)
    out = grants[["grant_id", "opportunity_title", "hard_filtered"]].copy()
    out["baseline_score"] = sim.max(axis=1).round(5)
    out["baseline_best_match"] = [keys[i] for i in sim.argmax(axis=1)]
    # Rank only grants that reach Layer 2, so it is comparable with Jev's routing.
    live = ~out["hard_filtered"].astype(bool)
    out["baseline_rank"] = pd.NA
    out.loc[live, "baseline_rank"] = out.loc[live, "baseline_score"].rank(ascending=False, method="first").astype(int)
    return out.sort_values("baseline_score", ascending=False)


def run() -> pd.DataFrame:
    grants = pd.read_csv(config.LAYER1_OUTPUT)
    out = score(grants, config.load_agency())
    config.RESULTS.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT, index=False)
    print(f"Keyword baseline: scored {len(out)} grants -> {OUTPUT}")
    print(out[~out["hard_filtered"]].head(8)[["baseline_rank", "baseline_score", "opportunity_title"]]
          .to_string(index=False, max_colwidth=70))
    return out


if __name__ == "__main__":
    run()
