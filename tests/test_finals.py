"""Tests for the finals matchmaker: API mapping, scoring signals, AI checks, evaluation, storage, web app."""

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import config  # noqa: E402
import evaluate  # noqa: E402
import matcher  # noqa: E402
import normalize  # noqa: E402
import rationale  # noqa: E402
from storage import ConflictError, LocalStore, Store, set_store  # noqa: E402

AGENCY = config.load_agency()

POSTED_HIT = {"id": "1001", "number": "CDC-RFA-26-0001", "title": "State Overdose Data to Action &ndash; States",
              "agencyCode": "HHS-CDC", "agency": "Centers for Disease Control", "openDate": "10/01/2026",
              "closeDate": "12/31/2026", "oppStatus": "posted", "docType": "synopsis", "cfdaList": ["93.136"]}
POSTED_DETAIL = {
    "id": 1001, "opportunityNumber": "CDC-RFA-26-0001", "opportunityTitle": "State Overdose Data to Action",
    "opportunityCategory": {"description": "Discretionary"}, "docType": "synopsis",
    "cfdas": [{"cfdaNumber": "93.136", "programTitle": "Injury Prevention and Control Research and State and Community Based Programs"}],
    "synopsis": {
        "synopsisDesc": "<p>This cooperative agreement funds state health departments to prevent opioid overdose "
                        "deaths through surveillance and harm reduction programs across the state.</p>",
        "responseDateStr": "2026-12-31-00-00-00", "postingDateStr": "2026-10-01-00-00-00",
        "archiveDateStr": "2027-01-30-00-00-00", "costSharing": False, "numberOfAwards": 50,
        "estimatedFunding": 100000000, "awardCeiling": 4000000, "awardFloor": 1000000,
        "applicantEligibilityDesc": "Eligible applicants are state health departments.",
        "applicantTypes": [{"id": "00", "description": "State governments"}],
        "fundingInstruments": [{"id": "CA", "description": "Cooperative Agreement"}],
        "fundingActivityCategories": [{"id": "HL", "description": "Health"}],
        "agencyDetails": {"agencyName": "Centers for Disease Control"},
        "topAgencyDetails": {"agencyName": "Department of Health and Human Services"},
        "createTimeStampStr": "2026-10-01-00-00-00",
    },
}
FORECAST_HIT = {"id": "1002", "number": "HRSA-27-001", "title": "Rural Health Network Development", "agencyCode": "HHS-HRSA",
                "agency": "Health Resources and Services Administration", "openDate": "", "closeDate": "",
                "oppStatus": "forecasted", "docType": "forecast", "cfdaList": ["93.912"]}
FORECAST_DETAIL = {
    "id": 1002, "docType": "forecast", "cfdas": [{"cfdaNumber": "93.912", "programTitle": "Rural Health Care"}],
    "forecast": {"forecastDesc": "Supports rural health networks that improve access to primary care and telehealth in rural communities.",
                 "estSynopsisPostingDateStr": "2027-01-15-00-00-00", "estApplicationResponseDateStr": "2027-03-15-00-00-00",
                 "costSharing": True, "awardCeiling": 300000, "applicantTypes": [{"id": "12"}, {"id": "25"}],
                 "applicantEligibilityDesc": "Rural nonprofit organizations.", "agencyDetails": {"agencyName": "HRSA"},
                 "topAgencyDetails": {"agencyName": "Department of Health and Human Services"}},
}
CLOSED_HIT = {**POSTED_HIT, "id": "1003", "number": "OLD-1", "title": "Old grant", "closeDate": "01/15/2026"}
CLOSED_DETAIL = json.loads(json.dumps(POSTED_DETAIL).replace("2026-12-31-00-00-00", "2026-01-15-00-00-00"))
DUP_HIT = {**POSTED_HIT, "id": "1004"}


def live_frame():
    hits = [POSTED_HIT, FORECAST_HIT, CLOSED_HIT, DUP_HIT]
    details = {"1001": POSTED_DETAIL, "1002": FORECAST_DETAIL, "1003": CLOSED_DETAIL, "1004": POSTED_DETAIL}
    return normalize.normalize(hits, details, "2026-11-07", AGENCY)


# ── Normalize ──

def test_api_row_maps_fields():
    row = normalize.api_to_row(POSTED_HIT, POSTED_DETAIL)
    assert row["opportunity_title"] == "State Overdose Data to Action – States"  # HTML entity decoded
    assert row["close_date"] == "2026-12-31"
    assert row["applicant_types"] == "state_governments"
    assert row["opportunity_assistance_listings"].startswith("93.136|")
    assert row["is_forecast"] == "False"
    f = normalize.api_to_row(FORECAST_HIT, FORECAST_DETAIL)
    assert f["is_forecast"] == "True" and f["close_date"] == "" and f["forecasted_close_date"] == "2027-03-15"
    assert f["applicant_types"] == "nonprofits_non_higher_education_with_501c3;other"


def test_normalize_drops_closed_and_duplicates_and_flags_quality():
    live, stats = live_frame()
    assert stats["records_in"] == 4
    assert stats["duplicates_dropped"] == 1
    assert stats["dropped_closed_or_admin"] == 1
    assert set(live["opportunity_number"]) == {"CDC-RFA-26-0001", "HRSA-27-001"}
    posted = live[live["opportunity_number"] == "CDC-RFA-26-0001"].iloc[0]
    assert posted["days_until_close"] == 54
    rec = normalize.minimum_record(posted, "2026-11-07T11:00:00+00:00")
    for k in ["id", "source", "number", "title", "agency", "status", "open_date", "close_date", "days_to_close",
              "eligibility", "category", "award_ceiling", "description", "url", "ingested_at"]:
        assert k in rec
    assert rec["url"].endswith("/1001")


def test_missing_detail_is_flagged_not_dropped():
    live, stats = normalize.normalize([POSTED_HIT], {}, "2026-11-07", AGENCY)
    assert len(live) == 1 and bool(live.iloc[0]["low_quality"])
    assert "no detail record" in live.iloc[0]["quality_issues"]


# ── Scoring ──

@pytest.fixture()
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.delenv("AOAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AOAI_KEY", raising=False)
    s = Store(LocalStore(tmp_path))
    s.write_json("cache/aln_history.json", {})  # no network in tests
    set_store(s)
    yield s
    set_store(None)


def test_score_breakdown_sums_to_total(tmp_store, monkeypatch):
    monkeypatch.setattr(matcher, "aln_affinity", lambda *a, **k: {})
    live, _ = live_frame()
    scored, meta = matcher.score(live, AGENCY, tmp_store, log=lambda *_: None)
    assert meta["method"] == "tfidf"
    w = meta["weights"]
    assert abs(sum(w.values()) - 1) < 1e-9
    for _, r in scored.iterrows():
        b = matcher.breakdown(r, w)
        assert abs(sum(x["points"] for x in b) - r["score"]) < 0.3
        assert 0 <= r["score"] <= 100
    cdc = scored[scored["opportunity_number"] == "CDC-RFA-26-0001"].iloc[0]
    assert cdc["matched_goal_id"] == "G3"           # opioid overdose -> behavioral health goal
    assert cdc["s_eligibility"] == 1.0 and cdc["track"] == "agency"
    hrsa = scored[scored["opportunity_number"] == "HRSA-27-001"].iloc[0]
    assert hrsa["s_eligibility"] == 0.4             # nonprofits + 'other': unclear, not excluded


def test_eligibility_and_timing_signals():
    base = {"text_higher_ed_only": False, "text_tribal_only": False, "text_individuals_only": False,
            "state_government_listed": False, "text_mentions_state_agency": False, "unrestricted_listed": False,
            "other_listed": False, "applicant_types_blank": False}
    assert matcher.eligibility_signal(pd.Series({**base, "state_government_listed": True}))[0] == 1.0
    assert matcher.eligibility_signal(pd.Series({**base, "state_government_listed": True, "text_higher_ed_only": True}))[0] == 0.0
    assert matcher.eligibility_signal(pd.Series(base))[0] == 0.0
    t = {"is_forecast": True, "forecast_close_passed": True, "rolling_deadline": False}
    assert matcher.timing_signal(pd.Series(t))[0] == 0.3
    t = {"is_forecast": False, "rolling_deadline": False, "days_until_close": 5, "deadline_score": 1.43}
    assert matcher.timing_signal(pd.Series(t))[0] == pytest.approx(0.143)


def test_keyword_hits_title_counts_double():
    pats = matcher.keyword_patterns(["opioid", "WIC", "988"])
    t, b = matcher.keyword_hits("Opioid response", "Funds 988 crisis lines; the WICKED project", pats)
    assert t == ["opioid"] and b == ["988"]      # 'WICKED' is not 'WIC'


# ── AI checks ──

def scored_row():
    live, _ = live_frame()
    r = live[live["opportunity_number"] == "CDC-RFA-26-0001"].iloc[0].copy()
    r["matched_goal_id"], r["matched_objective_id"], r["s_eligibility"] = "G3", "G3.O4", 1.0
    return r


def test_ai_check_catches_fabricated_quote_and_unsupported_ineligible():
    r = scored_row()
    ans = {"summary": "s", "why_it_matches": "w", "fits_matched_goal": True, "better_goal_id": "",
           "evidence_quote": "funds state health departments to prevent opioid overdose deaths",
           "applicant_role": "ineligible", "eligibility_notes": "n",
           "eligibility_quote": "Only universities may apply.", "owning_division": "NOPE",
           "deadline_note": "d", "risk_or_gap": "r"}
    clean, problems = rationale.check(ans, r, AGENCY)
    kinds = {p["kind"] for p in problems}
    assert clean["evidence_verified"] is True
    assert clean["eligibility_verified"] is False
    assert clean["applicant_role"] == "unclear"          # unverified 'ineligible' is not trusted
    assert clean["owning_division"] == ""
    assert {"quote_not_in_source", "unsupported_claim", "invalid_value"} <= kinds


def test_ai_can_only_move_or_downgrade_never_rescore():
    df = pd.DataFrame([{"grant_id": "a", "score": 70.0, "confidence": "High", "track": "agency", "matched_objective_id": "G3.O4"},
                       {"grant_id": "b", "score": 65.0, "confidence": "High", "track": "agency", "matched_objective_id": "G1.O1"},
                       {"grant_id": "c", "score": 60.0, "confidence": "High", "track": "agency", "matched_objective_id": "G2.O1"}])
    reviews = {"a": {"applicant_role": "ineligible", "eligibility_verified": True, "fits_matched_goal": True},
               "b": {"applicant_role": "lead", "eligibility_verified": True, "fits_matched_goal": False}}
    out = rationale.apply(df, reviews).set_index("grant_id")
    assert out.loc["a", "track"] == "not_eligible"
    assert out.loc["b", "confidence"] == "Medium"
    assert out.loc["c", "confidence"] == "High"
    assert list(out["score"]) == [70.0, 65.0, 60.0]


# ── Evaluation ──

def rec(i, conf="High", kws=(), track="agency"):
    return {"id": str(i), "title": f"t{i}", "track": track, "confidence": conf, "score": 100 - i,
            "keywords_matched": list(kws), "keywords_in_title": []}


def test_metrics_precision_recall_agreement():
    recs = [rec(i, kws=["x"] * (i % 3)) for i in range(40)]
    doc = {"run_id": "r", "as_of": "2026-11-07", "records": recs}
    sample = evaluate.draw_sample(doc)
    ids = [it["id"] for it in sample["items"]]
    assert len(ids) == len(set(ids)) and 20 <= len(ids) <= 30
    labels = []
    for i in range(10):
        labels.append({"id": str(i), "labeler": "A", "relevant": i < 8})
        labels.append({"id": str(i), "labeler": "B", "relevant": i < 7})
    m = evaluate.metrics(doc, sample, labels, {}, None)
    # item 7 is a 1-1 tie: left unjudged until a third vote (e.g. after the team discusses it)
    assert m["ours_p10"] == {"k": 10, "judged": 9, "relevant": 7, "precision": 0.78}
    assert m["agreement"]["pairs"] == 10 and m["agreement"]["agree"] == 9
    assert len(m["disagreements"]) == 1


def test_labeler_order_is_shuffled_per_person_but_complete():
    sample = {"items": [{"id": str(i)} for i in range(25)]}
    a = [x["id"] for x in evaluate.labeler_order(sample, "Alex")]
    b = [x["id"] for x in evaluate.labeler_order(sample, "Blake")]
    assert sorted(a) == sorted(b) and a != b


# ── Storage ──

def test_update_json_detects_conflicts(tmp_path):
    s = Store(LocalStore(tmp_path))
    s.update_json("d.json", lambda cur: {"n": cur["n"] + 1}, default={"n": 0})
    s.update_json("d.json", lambda cur: {"n": cur["n"] + 1}, default={"n": 0})
    assert s.read_json("d.json") == {"n": 2}
    v = s.version("d.json")
    s.write_json("d.json", {"n": 99})
    import os, time
    os.utime(tmp_path / "d.json", ns=(time.time_ns(), time.time_ns() + 10))
    with pytest.raises(ConflictError):
        s.b.write_if_version("d.json", b"{}", v)


def test_local_store_rejects_path_escape(tmp_path):
    with pytest.raises(ValueError):
        LocalStore(tmp_path).read_bytes("../outside.json")


# ── Web app ──

@pytest.fixture()
def client(tmp_store, monkeypatch):
    monkeypatch.setattr(matcher, "aln_affinity", lambda *a, **k: {})
    import job
    import grantsgov
    hits = [POSTED_HIT, FORECAST_HIT] + [{**FORECAST_HIT, "id": str(2000 + i), "number": f"F-{i}"} for i in range(60)]
    details = {h["id"]: (POSTED_DETAIL if h["id"] == "1001" else FORECAST_DETAIL) for h in hits}
    monkeypatch.setattr(grantsgov, "ingest", lambda store, kws, today, log: {
        "hits": hits, "details": details, "keyword_hits": {"opioid": ["1001"]}, "stats": {"pulled": len(hits)}, "errors": []})
    job.run(log=lambda *_: None)
    import webapp
    webapp._cache.clear()
    webapp.app.config["TESTING"] = True
    return webapp.app.test_client()


def _csrf(client, path):
    html = client.get(path).get_data(as_text=True)
    return html.split('name="csrf" value="')[1].split('"')[0]


def test_pages_render(client):
    for path in ["/", "/?track=all&confidence=all", "/goals", "/evaluation", "/status", "/profile", "/method",
                 "/opportunity/1001", "/healthz", "/export.csv"]:
        r = client.get(path)
        assert r.status_code == 200, path
    assert client.get("/opportunity/does-not-exist").status_code == 404
    assert "Content-Security-Policy" in client.get("/").headers


def test_decision_requires_csrf_and_is_saved(client, tmp_store):
    assert client.post("/opportunity/1001/decision", data={"decision": "Pursue"}).status_code == 400
    token = _csrf(client, "/opportunity/1001")
    r = client.post("/opportunity/1001/decision", data={"csrf": token, "decision": "Pursue", "name": "PP", "note": "route to DMH"})
    assert r.status_code == 302
    saved = tmp_store.read_json("decisions/ncdhhs.json")["decisions"]["1001"][-1]
    assert saved["decision"] == "Pursue" and saved["by"] == "PP" and saved["note"] == "route to DMH"
    assert "Pursue" in client.get("/export.csv?track=all&confidence=all").get_data(as_text=True)
    bad = client.post("/opportunity/1001/decision", data={"csrf": token, "decision": "Maybe", "next": "//evil.example"})
    assert bad.headers["Location"].endswith("/opportunity/1001")


def test_labeling_flow(client, tmp_store):
    token = _csrf(client, "/evaluation")
    assert client.post("/evaluation/sample", data={"csrf": token}).status_code == 302
    sample = tmp_store.read_json("eval/ncdhhs/sample.json")
    first = sample["items"][0]["id"]
    r = client.post("/evaluation/label", data={"csrf": token, "id": first, "labeler": "A", "relevant": "yes"})
    assert r.status_code == 302
    assert tmp_store.read_json("eval/ncdhhs/labels.json")["labels"][0]["relevant"] is True
    assert client.get("/evaluation").status_code == 200


# ── Review fixes ──

def test_csv_cells_cannot_run_formulas():
    import webapp
    assert webapp.cell("=HYPERLINK(1)") == "'=HYPERLINK(1)"
    assert webapp.cell("+1") == "'+1" and webapp.cell("@x") == "'@x" and webapp.cell("-2") == "'-2"
    assert webapp.cell("Plain text") == "Plain text" and webapp.cell(42) == 42 and webapp.cell(None) == ""


def test_safe_next_rejects_offsite_and_control_characters():
    import webapp
    assert webapp.safe_next("/?q=1#opp-2", "/x") == "/?q=1#opp-2"
    for bad in ["//evil.example", "https://evil.example", "/\t/evil.example", r"/\evil", "/a\r\nb", ""]:
        assert webapp.safe_next(bad, "/x") == "/x", bad


def test_quick_decision_without_a_name_is_not_saved(client, tmp_store):
    with client.session_transaction() as s:
        s.pop("name", None)
    token = _csrf(client, "/")
    r = client.post("/opportunity/1001/decision", data={"csrf": token, "decision": "Pass"})
    assert r.status_code == 302 and "#dec-h" in r.headers["Location"]
    assert not (tmp_store.read_json("decisions/ncdhhs.json") or {}).get("decisions", {}).get("1001")
    client.post("/name", data={"csrf": token, "name": "AB", "next": "/"})
    client.post("/opportunity/1001/decision", data={"csrf": token, "decision": "Pass"})
    client.post("/opportunity/1001/decision", data={"csrf": token, "decision": "Pass"})   # double click
    hist = tmp_store.read_json("decisions/ncdhhs.json")["decisions"]["1001"]
    assert len(hist) == 1 and hist[0]["by"] == "AB"


def test_records_closed_since_the_refresh_are_hidden(client, monkeypatch):
    import webapp
    from datetime import date
    webapp._cache.clear()
    monkeypatch.setattr(webapp, "today_et", lambda: date(2027, 1, 5))    # after the CDC close date
    html = client.get("/?track=all&confidence=all&q=Overdose").get_data(as_text=True)
    assert "State Overdose Data to Action" not in html
    monkeypatch.setattr(webapp, "today_et", lambda: date(2026, 12, 30))
    webapp._cache.clear()
    html = client.get("/?track=all&confidence=all&q=Overdose").get_data(as_text=True)
    assert "State Overdose Data to Action" in html and "1 days" in html


def test_label_page_uses_snapshot_when_item_is_gone(client, tmp_store):
    token = _csrf(client, "/evaluation")
    client.post("/evaluation/sample", data={"csrf": token})
    sample = tmp_store.read_json("eval/ncdhhs/sample.json")
    assert all("snapshot" in it for it in sample["items"])
    # Keep only an item that is no longer in today's results.
    sample["items"] = [{"id": "gone", "stratum": "test", "title": "Closed grant",
                        "snapshot": {"number": "X-1", "agency": "A", "status": "posted", "close_date": "2026-11-08",
                                     "eligibility": "state_governments", "url": "https://www.grants.gov/x",
                                     "description": "desc", "eligibility_text": ""}}]
    tmp_store.write_json("eval/ncdhhs/sample.json", sample)
    page = client.get("/evaluation/label?labeler=A").get_data(as_text=True)
    assert "Closed grant" in page and "you labeled all" not in page     # shown, not skipped as "done"


def test_new_since_compares_with_an_earlier_day(tmp_store, monkeypatch):
    import grantsgov
    import job
    monkeypatch.setattr(matcher, "aln_affinity", lambda *a, **k: {})
    hits = [POSTED_HIT, FORECAST_HIT] + [{**FORECAST_HIT, "id": str(3000 + i), "number": f"G-{i}"} for i in range(60)]
    details = {h["id"]: (POSTED_DETAIL if h["id"] == "1001" else FORECAST_DETAIL) for h in hits}
    monkeypatch.setattr(grantsgov, "ingest", lambda store, kws, today, log: {
        "hits": hits, "details": details, "keyword_hits": {}, "stats": {"pulled": len(hits)}, "errors": []})
    earlier = {"seen_ids": [h["id"] for h in hits if h["id"] != "1001"], "run_id": "old"}
    tmp_store.write_json("scored/ncdhhs/2000-01-01.json", earlier)
    for _ in range(2):                                   # a same-day re-run keeps the same alert
        job.run(log=lambda *_: None)
        assert tmp_store.read_json("alerts/ncdhhs/latest.json")["new_since_last_run"] == ["1001"]
    assert tmp_store.read_json("runs/last_attempt.json")["status"] == "succeeded"


def test_concurrent_decisions_are_never_lost(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    s = Store(LocalStore(tmp_path))
    with ThreadPoolExecutor(8) as pool:
        list(pool.map(lambda i: s.update_json("d.json", lambda cur: {"n": cur["n"] + [i]}, default={"n": []}), range(40)))
    assert sorted(s.read_json("d.json")["n"]) == list(range(40))


# ── Multi-agency ──

def test_every_profile_follows_the_template():
    profiles = config.load_profiles()
    assert [p["profile"]["agency_id"] for p in profiles][:1] == ["ncdhhs"] and len(profiles) >= 2
    for p in profiles:
        assert p["profile"]["plan_url"].startswith("https://www.osbm.nc.gov/")
        assert 20 <= len(p["profile"]["keywords"]) <= 40
        ids = [o["id"] for g in p["strategic_priorities"] for o in g["objectives"]]
        assert len(ids) == len(set(ids)) and len(ids) >= 15
        assert all(g.get("source") for g in p["strategic_priorities"])
        assert all(o.get("source") for g in p["strategic_priorities"] for o in g["objectives"])
        assert {"layer1", "layer5_award_history"} <= set(p)
        import re as _re
        _re.compile(p["profile"]["usaspending_recipient_pattern"])


def test_job_publishes_a_list_per_agency_and_the_app_switches(client, tmp_store):
    assert tmp_store.read_json("scored/ncdhhs/latest.json") and tmp_store.read_json("scored/ncdeq/latest.json")
    assert tmp_store.read_json("profiles/ncdeq.json")["agency_short"] == "NC DEQ"
    html = client.get("/?agency=ncdeq").get_data(as_text=True)
    assert "Funding opportunities for NC DEQ" in html
    assert "NCDEQ Strategic Plan" in client.get("/profile").get_data(as_text=True)     # remembered in the session
    page = client.get("/statewide").get_data(as_text=True)
    assert client.get("/statewide").status_code == 200 and "NC DHHS" in page and "NC DEQ" in page


def test_funder_history_uses_each_agencys_own_name():
    deq = next(p for p in config.load_profiles() if p["profile"]["agency_id"] == "ncdeq")
    hist = {"66.458": {"total": 5e8, "state_agency": 4e8, "university": 0, "tribal": 0, "local_government": 1e8,
                       "nonprofit_or_other": 0, "unclassified": 0, "nc_state_agency": 3e7, "top_recipients": "",
                       "nc_recipients": [{"name": "NORTH CAROLINA DEPARTMENT OF ENVIRONMENTAL QUALITY", "amount": 3e7}]}}
    s, reason, summary = matcher.affinity_signal(["66.458"], hist, deq["layer5_award_history"], True, deq)
    assert s == 1.0 and "NC DEQ received $30.0M" in reason and summary["agency"] == "NC DEQ"
