"""Daily ingestion from the Grants.gov public API (no key needed).

Two endpoints:
  search2           POST /v1/api/search2           -> ids, titles, dates (paged, max 1,000 rows a call)
  fetchOpportunity  POST /v1/api/fetchOpportunity  -> the full listing: description, eligibility,
                                                      award amounts, assistance listings

What one run does
  1. Broad pull: every posted and forecasted opportunity (no keyword). About 1,500 records.
  2. Keyword pulls: one search per profile keyword. Nothing is added from these; they record
     which opportunities a keyword-only search would have found, so the evaluation can show
     what keyword monitoring misses.
  3. Details: fetchOpportunity for every id in the broad pull. Details are cached in storage
     (details/{id}.json) and fetched again only when the listing changed (new close date or
     status) or the cached copy is older than DETAIL_MAX_AGE_DAYS.
  4. Saves the untouched responses to raw/{yyyy-mm-dd}/grants.json for audit and replay.

One bad page or listing never stops the run: it is retried, then counted as an error.
"""

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests

API = "https://api.grants.gov/v1/api"
PAGE_ROWS = 1000
MAX_RECORDS = 5000            # safety cap for the broad pull
DETAIL_MAX_AGE_DAYS = 7
WORKERS = 8
TIMEOUT_S = 45

_session = requests.Session()
_session.headers.update({"Content-Type": "application/json", "User-Agent": "ffm-matchmaker/1.0 (prototype)"})


def _post(endpoint: str, body: dict, retries: int = 4) -> dict:
    last = ""
    for attempt in range(retries):
        try:
            r = _session.post(f"{API}/{endpoint}", json=body, timeout=TIMEOUT_S)
            if r.status_code == 200:
                data = r.json()
                if str(data.get("errorcode", 0)) not in ("0", "None"):
                    raise RuntimeError(f"API error {data.get('errorcode')}: {data.get('msg')}")
                return data.get("data") or {}
            last = f"HTTP {r.status_code}"
        except (requests.RequestException, ValueError, RuntimeError) as e:
            last = str(e)[:200]
        time.sleep(1.5 * 2 ** attempt)
    raise RuntimeError(f"{endpoint} failed after {retries} tries: {last}")


def search(keyword: str = "", statuses: str = "forecasted|posted", cap: int = MAX_RECORDS) -> tuple[list[dict], int]:
    """All hits for one query, paged. Returns (hits, hitCount reported by the API)."""
    hits, start, total = [], 0, None
    while True:
        data = _post("search2", {"keyword": keyword, "oppStatuses": statuses, "rows": PAGE_ROWS,
                                 "startRecordNum": start})
        page = data.get("oppHits") or []
        total = int(data.get("hitCount") or 0) if total is None else total
        hits += page
        start += len(page)
        if not page or start >= total or start >= cap:
            break
    return hits, total


def fetch_detail(opp_id: str) -> dict:
    return _post("fetchOpportunity", {"opportunityId": int(opp_id)})


def _fingerprint(hit: dict) -> str:
    return "|".join(str(hit.get(k, "")) for k in ("closeDate", "oppStatus", "openDate", "title"))


def ingest(store, keywords: list[str], today: str, log=print) -> dict:
    """Run steps 1-4. Returns {'hits', 'details', 'keyword_hits', 'stats', 'errors'}."""
    t0 = time.time()
    errors: list[str] = []

    hits, reported = search("")
    seen, unique = set(), []
    for h in hits:
        if h.get("id") and h["id"] not in seen:
            seen.add(h["id"])
            unique.append(h)
    log(f"  broad pull: {len(unique)} unique opportunities (API reported {reported})")

    keyword_hits: dict[str, list[str]] = {}

    def kw(k):
        try:
            got, _ = search(k, cap=2000)
            return k, [h["id"] for h in got if h.get("id")]
        except RuntimeError as e:
            errors.append(f"keyword '{k}': {e}")
            return k, None

    with ThreadPoolExecutor(4) as pool:
        for k, ids in pool.map(kw, keywords):
            if ids is not None:
                keyword_hits[k] = ids
    log(f"  keyword pulls: {len(keyword_hits)}/{len(keywords)} keywords, "
        f"{len({i for v in keyword_hits.values() for i in v})} distinct ids")

    index = store.read_json("details/index.json", default={}) or {}
    now = datetime.now(timezone.utc)

    def stale(h) -> bool:
        meta = index.get(h["id"])
        if not meta or meta.get("fp") != _fingerprint(h):
            return True
        age = (now - datetime.fromisoformat(meta["fetched_at"])).days
        return age >= DETAIL_MAX_AGE_DAYS

    todo = [h for h in unique if stale(h)]
    log(f"  details: {len(unique) - len(todo)} cached, {len(todo)} to fetch")
    details: dict[str, dict] = {}

    def one(h):
        try:
            d = fetch_detail(h["id"])
            store.write_json(f"details/{h['id']}.json", d)
            return h, d, None
        except RuntimeError as e:
            return h, None, f"detail {h['id']}: {e}"

    with ThreadPoolExecutor(WORKERS) as pool:
        for h, d, err in pool.map(one, todo):
            if err:
                errors.append(err)
            else:
                details[h["id"]] = d
                index[h["id"]] = {"fp": _fingerprint(h), "fetched_at": now.isoformat()}
    for h in unique:
        if h["id"] not in details:
            cached = store.read_json(f"details/{h['id']}.json")
            if cached is not None:
                details[h["id"]] = cached
    store.write_json("details/index.json", index)

    store.write_json(f"raw/{today}/grants.json", {
        "pulled_at": now.isoformat(), "source": f"{API}/search2 + fetchOpportunity",
        "query": {"oppStatuses": "forecasted|posted", "keyword": ""}, "hit_count_reported": reported,
        "hits": unique, "keyword_hits": keyword_hits})
    stats = {"pulled": len(unique), "reported": reported, "details_fetched": len(todo) - sum(e.startswith("detail") for e in errors),
             "details_cached": len(unique) - len(todo), "details_missing": len(unique) - len(details),
             "keywords": len(keyword_hits), "seconds": round(time.time() - t0, 1)}
    return {"hits": unique, "details": details, "keyword_hits": keyword_hits, "stats": stats, "errors": errors}
