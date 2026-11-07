"""Staff-facing web app (MODE=app): the ranked shortlist, details, decisions, export, evaluation, run status.

    python src/webapp.py            # http://localhost:8000 (reads the same storage as the job)
    gunicorn --chdir src webapp:app # how the container runs it

Plain server-rendered HTML forms: works without JavaScript, with a keyboard and a screen reader,
and on a phone. Nothing here calls an AI model; it only reads what the daily job wrote and saves
staff decisions and evaluation labels.
"""

import csv
import io
import os
import secrets
import time
from datetime import datetime, timezone
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from flask import Flask, Response, abort, flash, redirect, render_template, request, session, url_for

import config
import evaluate
from storage import get_store

ET = ZoneInfo("America/New_York")
AGENCY = config.load_agency()
AID = AGENCY["profile"]["agency_id"]
DECISIONS = f"decisions/{AID}.json"
CHOICES = ("Pursue", "Maybe", "Pass")
PAGE_SIZE = 50
TRACKS = {"agency": "Agency can apply", "research": "Research (university partner)", "not_eligible": "Not eligible"}

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "1") == "1" and os.getenv("MODE") == "app")


# ── Data (cached; re-read only when the blob changes, checked at most every 30 s) ──

_cache: dict = {}


def _cached(path: str, default):
    store = get_store()
    entry = _cache.get(path)
    if entry and time.time() - entry["checked"] < 30:
        return entry["value"]
    version = store.version(path)
    if entry and entry["version"] == version:
        entry["checked"] = time.time()
        return entry["value"]
    value = store.read_json(path, default=default)
    _cache[path] = {"version": version, "value": value, "checked": time.time()}
    return value


def scored() -> dict | None:
    return _cached(f"scored/{AID}/latest.json", None)


def decisions() -> dict:
    return (get_store().read_json(DECISIONS, default={}) or {}).get("decisions", {})


def labels() -> list:
    return (get_store().read_json(evaluate.LABELS_PATH, default={}) or {}).get("labels", [])


def latest_run() -> dict | None:
    return _cached("runs/latest.json", None)


# ── Helpers available in templates ──

def fmt_dt(iso: str | None) -> str:
    if not iso:
        return "never"
    dt = datetime.fromisoformat(iso).astimezone(ET)
    return dt.strftime("%a %-d %b %Y, %-I:%M %p ET") if os.name != "nt" else dt.strftime("%a %d %b %Y, %I:%M %p ET")


def money(v) -> str:
    if v is None:
        return "not stated"
    return f"${v / 1e6:,.1f}M" if v >= 1e6 else f"${v:,.0f}"


@app.context_processor
def inject():
    return {"fmt_dt": fmt_dt, "money": money, "agency": AGENCY, "TRACKS": TRACKS, "csrf_token": csrf_token,
            "goals": {g["id"]: g for g in AGENCY["strategic_priorities"]},
            "divisions": {d["id"]: d for d in AGENCY["divisions"]}, "run": latest_run()}


def csrf_token() -> str:
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


@app.before_request
def check_csrf():
    if request.method == "POST":
        if not session.get("csrf") or request.form.get("csrf") != session.get("csrf"):
            abort(400, "Your form expired. Go back, reload the page and try again.")


@app.after_request
def security_headers(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "same-origin")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Content-Security-Policy",
                            "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; form-action 'self'")
    return resp


# ── Filtering ──

FILTER_KEYS = ("q", "track", "confidence", "status", "within", "goal", "division", "decision", "sort")


def current_filters() -> dict:
    f = {k: request.args.get(k, "").strip() for k in FILTER_KEYS}
    f["track"] = f["track"] or "agency"
    f["confidence"] = f["confidence"] or "hm"   # High + Medium by default; Low is hidden
    return f


def apply_filters(records: list[dict], f: dict, decided: dict) -> list[dict]:
    out = []
    q = f["q"].lower()
    for r in records:
        if f["track"] != "all" and r["track"] != f["track"]:
            continue
        if f["confidence"] == "hm" and r["confidence"] == "Low":
            continue
        if f["confidence"] in ("High", "Medium", "Low") and r["confidence"] != f["confidence"]:
            continue
        if f["status"] in ("posted", "forecasted") and r["status"] != f["status"]:
            continue
        if f["within"]:
            try:
                n = int(f["within"])
            except ValueError:
                n = None
            if n is not None and (r["days_to_close"] is None or not 0 <= r["days_to_close"] <= n):
                continue
        if f["goal"] and r["matched_goal"]["id"] != f["goal"]:
            continue
        if f["division"] and ((r.get("ai") or {}).get("owning_division") != f["division"]):
            continue
        d = (decided.get(r["id"]) or [{}])[-1].get("decision", "")
        if f["decision"] == "none" and d:
            continue
        if f["decision"] in CHOICES and d != f["decision"]:
            continue
        if q and q not in f"{r['title']} {r['number']} {r['agency']} {r['description']}".lower():
            continue
        out.append(r)
    if f["sort"] == "deadline":
        out.sort(key=lambda r: (r["days_to_close"] is None, r["days_to_close"] if r["days_to_close"] is not None else 0))
    elif f["sort"] == "newest":
        out.sort(key=lambda r: r.get("open_date") or "", reverse=True)
    return out


def query_with(f: dict, **changes) -> str:
    merged = {**{k: v for k, v in f.items() if v}, **changes}
    return urlencode({k: v for k, v in merged.items() if v not in ("", None)})


# ── Pages ──

@app.route("/")
def shortlist():
    doc = scored()
    if not doc:
        return render_template("empty.html")
    f = current_filters()
    decided = decisions()
    rows = apply_filters(doc["records"], f, decided)
    page = max(1, request.args.get("page", 1, type=int))
    pages = max(1, (len(rows) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, pages)
    alerts = get_store().read_json(f"alerts/{AID}/latest.json", default={}) or {}
    by_id = {r["id"]: r for r in doc["records"]}
    return render_template("shortlist.html", doc=doc, rows=rows[(page - 1) * PAGE_SIZE: page * PAGE_SIZE],
                           total=len(rows), page=page, pages=pages, f=f, decided=decided, query_with=query_with,
                           new_items=[by_id[i] for i in alerts.get("new_since_last_run", []) if i in by_id],
                           closing=[by_id[i] for i in alerts.get("closing_soon", []) if i in by_id],
                           first_run=alerts.get("first_run", True))


@app.route("/opportunity/<oid>")
def detail(oid):
    doc = scored()
    rec = next((r for r in (doc or {}).get("records", []) if r["id"] == oid), None)
    if rec is None:
        abort(404)
    hist = decisions().get(oid, [])
    return render_template("detail.html", r=rec, history=hist, doc=doc,
                           name=session.get("name", ""), back=request.args.get("back", ""))


@app.route("/opportunity/<oid>/decision", methods=["POST"])
def decide(oid):
    doc = scored()
    rec = next((r for r in (doc or {}).get("records", []) if r["id"] == oid), None)
    if rec is None:
        abort(404)
    choice = request.form.get("decision", "")
    if choice not in CHOICES:
        abort(400, "Choose Pursue, Maybe or Pass.")
    name = request.form.get("name", "").strip()[:60] or session.get("name", "") or "staff"
    session["name"] = name
    entry = {"decision": choice, "by": name, "note": request.form.get("note", "").strip()[:1000],
             "at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
             "score_at_decision": rec["score"], "confidence_at_decision": rec["confidence"], "run_id": doc["run_id"]}

    def add(cur):
        cur = cur or {"decisions": {}}
        cur.setdefault("decisions", {}).setdefault(oid, []).append(entry)
        return cur
    get_store().update_json(DECISIONS, add, default={"decisions": {}})
    flash(f"Saved: {choice} on “{rec['title'][:80]}”.")
    nxt = request.form.get("next", "")
    return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("detail", oid=oid))


@app.route("/export.csv")
def export():
    doc = scored()
    if not doc:
        abort(404)
    f = current_filters()
    decided = decisions()
    rows = apply_filters(doc["records"], f, decided)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["rank", "score", "confidence", "title", "opportunity_number", "funder", "status", "close_date",
                "days_to_close", "award_ceiling", "matched_goal", "matched_objective", "why_it_matches",
                "risk_or_gap", "owning_division", "decision", "decided_by", "decision_note", "grants_gov_link"])
    for r in rows:
        ai = r.get("ai") or {}
        d = (decided.get(r["id"]) or [{}])[-1]
        why = ai.get("why_it_matches") or "; ".join(b["reason"] for b in r["breakdown"][:2])
        w.writerow([r["rank"], r["score"], r["confidence"], r["title"], r["number"], r["agency"], r["status"],
                    r["close_date"], "" if r["days_to_close"] is None else r["days_to_close"],
                    "" if r["award_ceiling"] is None else int(r["award_ceiling"]),
                    f"{r['matched_goal']['id']} {r['matched_goal']['name']}", r["matched_objective"]["id"], why,
                    ai.get("risk_or_gap", ""), ai.get("owning_division", ""), d.get("decision", ""), d.get("by", ""),
                    d.get("note", ""), r["url"]])
    name = f"ncdhhs-shortlist-{doc['as_of']}.csv"
    return Response("﻿" + buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={name}"})


@app.route("/goals")
def goals_view():
    doc = scored()
    if not doc:
        return render_template("empty.html")
    rows = []
    agency_recs = [r for r in doc["records"] if r["track"] == "agency"]
    for g in AGENCY["strategic_priorities"]:
        rs = [r for r in agency_recs if r["matched_goal"]["id"] == g["id"]]
        strong = [r for r in rs if r["confidence"] in ("High", "Medium")]
        objs = []
        for o in g["objectives"]:
            ro = [r for r in strong if r["matched_objective"]["id"] == o["id"]]
            objs.append({"o": o, "n": len(ro), "top": ro[:3]})
        rows.append({"g": g, "high": sum(r["confidence"] == "High" for r in rs),
                     "medium": sum(r["confidence"] == "Medium" for r in rs),
                     "posted": sum(r["status"] == "posted" for r in strong),
                     "forecast": sum(r["status"] == "forecasted" for r in strong),
                     "closing30": sum(1 for r in strong if r["days_to_close"] is not None and r["days_to_close"] <= 30),
                     "ceiling": sum(r["award_ceiling"] or 0 for r in strong), "objectives": objs})
    peak = max([r["high"] + r["medium"] for r in rows] + [1])
    return render_template("goals.html", rows=rows, peak=peak, doc=doc)


@app.route("/evaluation")
def evaluation():
    doc = scored()
    if not doc:
        return render_template("empty.html")
    store = get_store()
    sample = store.read_json(evaluate.SAMPLE_PATH)
    kw = (store.read_json("eval/keyword_baseline/latest.json", default={}) or {}).get("keyword_hits")
    m = evaluate.metrics(doc, sample, labels(), decisions(), kw)
    by_id = {r["id"]: r for r in doc["records"]}
    return render_template("evaluation.html", m=m, sample=sample, by_id=by_id, doc=doc)


@app.route("/evaluation/sample", methods=["POST"])
def make_sample():
    doc = scored()
    store = get_store()
    if store.read_json(evaluate.SAMPLE_PATH) and request.form.get("confirm") != "replace":
        flash("A sample already exists. Labels are kept with their items.")
        return redirect(url_for("evaluation"))
    store.write_json(evaluate.SAMPLE_PATH, evaluate.draw_sample(doc), indent=2)
    flash("Labeling sample drawn: our top 10, the keyword baseline's top 10, and 10 more from the rest.")
    return redirect(url_for("label"))


@app.route("/evaluation/label", methods=["GET", "POST"])
def label():
    store = get_store()
    sample = store.read_json(evaluate.SAMPLE_PATH)
    if not sample:
        return redirect(url_for("evaluation"))
    if request.method == "POST":
        name = request.form.get("labeler", "").strip()[:40]
        if not name:
            abort(400, "Enter your name first.")
        session["labeler"] = name
        val = request.form.get("relevant")
        entry = {"id": request.form.get("id", ""), "labeler": name, "note": request.form.get("note", "").strip()[:500],
                 "relevant": True if val == "yes" else False if val == "no" else None,
                 "at": datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
        if entry["id"] not in {i["id"] for i in sample["items"]}:
            abort(400)
        store.update_json(evaluate.LABELS_PATH, lambda cur: {"labels": (cur or {}).get("labels", []) + [entry]},
                          default={"labels": []})
        return redirect(url_for("label"))
    name = request.args.get("labeler", session.get("labeler", "")).strip()
    if not name:
        return render_template("label.html", name="", item=None, done=0, total=len(sample["items"]))
    session["labeler"] = name
    mine = {l["id"] for l in labels() if l["labeler"].strip().lower() == name.lower()}
    order = evaluate.labeler_order(sample, name)
    todo = [i for i in order if i["id"] not in mine]
    doc = scored()
    by_id = {r["id"]: r for r in (doc or {}).get("records", [])}
    item = by_id.get(todo[0]["id"]) if todo else None
    return render_template("label.html", name=name, item=item, done=len(order) - len(todo), total=len(order))


@app.route("/status")
def status():
    store = get_store()
    runs = []
    for p in sorted(store.list("runs/"), reverse=True):
        if p.endswith("latest.json"):
            continue
        runs.append(store.read_json(p))
        if len(runs) >= 14:
            break
    doc = scored()
    return render_template("status.html", runs=runs, doc=doc, storage=store.describe())


@app.route("/profile")
def profile():
    return render_template("profile.html", p=get_store().read_json(f"profiles/{AID}.json"))


@app.route("/method")
def method():
    return render_template("method.html", doc=scored())


@app.route("/healthz")
def healthz():
    run = latest_run()
    return {"ok": True, "last_run": (run or {}).get("run_id"), "storage": get_store().kind}


@app.errorhandler(400)
@app.errorhandler(404)
def error_page(e):
    return render_template("error.html", e=e), e.code


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")), debug=os.getenv("FLASK_DEBUG") == "1")
