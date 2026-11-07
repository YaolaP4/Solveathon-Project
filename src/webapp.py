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
from datetime import date
from urllib.parse import urlencode, urlsplit
from zoneinfo import ZoneInfo

from flask import Flask, Response, abort, flash, redirect, render_template, request, session, url_for

import config
import evaluate
from storage import get_store

ET = ZoneInfo("America/New_York")
PROFILES = config.load_profiles()                     # one standard profile per agency
BY_ID = {p["profile"]["agency_id"]: p for p in PROFILES}
DEFAULT_AID = PROFILES[0]["profile"]["agency_id"]
CHOICES = ("Pursue", "Maybe", "Pass")
PAGE_SIZE = 50
TRACKS = {"agency": "Agency can apply", "research": "Research (university partner)", "not_eligible": "Not eligible"}

app = Flask(__name__, template_folder="templates", static_folder="static")
if os.getenv("MODE") == "app" and not os.getenv("FLASK_SECRET_KEY"):
    # Every gunicorn worker must share one key, or form tokens fail at random.
    raise RuntimeError("FLASK_SECRET_KEY must be set when MODE=app")
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


def current_aid() -> str:
    """The agency being viewed: ?agency=... switches it (and is remembered), else the last one chosen."""
    a = request.args.get("agency", "")
    if a in BY_ID:
        session["agency"] = a
        return a
    a = session.get("agency", "")
    return a if a in BY_ID else DEFAULT_AID


def current_agency() -> dict:
    return BY_ID[current_aid()]


def decisions_path(aid: str | None = None) -> str:
    return f"decisions/{aid or current_aid()}.json"


def today_et() -> date:
    return datetime.now(ET).date()


def scored(aid: str | None = None) -> dict | None:
    """The latest results, with days-to-close recomputed for today, so a late or failed refresh
    never shows a deadline that has already passed as still open."""
    doc = _cached(f"scored/{aid or current_aid()}/latest.json", None)
    if doc and doc.get("_days_for") != today_et().isoformat():
        t = today_et()
        for r in doc["records"]:
            try:
                d = (date.fromisoformat(r["close_date"]) - t).days if r["status"] == "posted" else None
            except (TypeError, ValueError):
                d = None
            r["days_to_close"] = d
            r["closed_since_refresh"] = d is not None and d < 0
            r["closing_soon"] = d is not None and 0 <= d <= 10
        doc["_days_for"] = t.isoformat()
    return doc


def decisions(aid: str | None = None) -> dict:
    return (get_store().read_json(decisions_path(aid), default={}) or {}).get("decisions", {})


def labels() -> list:
    return (get_store().read_json(evaluate.labels_path(current_aid()), default={}) or {}).get("labels", [])


def latest_run() -> dict | None:
    return _cached("runs/latest.json", None)


def last_attempt() -> dict | None:
    return _cached("runs/last_attempt.json", None)


def refresh_warning() -> str:
    """Shown in red under the banner when the daily refresh failed or is overdue."""
    att, run = last_attempt(), latest_run()
    if att and att.get("status") == "failed":
        return (f"The last refresh attempt failed ({fmt_dt(att.get('finished_at'))}). "
                "The list below is from the last successful refresh.")
    if run and run.get("finished_at"):
        age_h = (datetime.now(ET) - datetime.fromisoformat(run["finished_at"]).astimezone(ET)).total_seconds() / 3600
        if age_h > 26:
            return f"No successful refresh for {age_h / 24:.0f} day(s). Check the Data refresh page."
    return ""


# ── Helpers available in templates ──

def fmt_dt(iso: str | None) -> str:
    if not iso:
        return "never"
    dt = datetime.fromisoformat(iso).astimezone(ET)
    return dt.strftime("%a %-d %b %Y, %-I:%M %p ET") if os.name != "nt" else dt.strftime("%a %d %b %Y, %I:%M %p ET")


APPLICANT_LABELS = {
    "state_governments": "State governments", "county_governments": "County governments",
    "city_or_township_governments": "City or township governments", "special_district_governments": "Special district governments",
    "independent_school_districts": "Independent school districts",
    "public_and_state_institutions_of_higher_education": "Public and state universities and colleges",
    "private_institutions_of_higher_education": "Private universities and colleges",
    "federally_recognized_native_american_tribal_governments": "Federally recognized tribal governments",
    "other_native_american_tribal_organizations": "Other Native American tribal organizations",
    "public_and_indian_housing_authorities": "Public and Indian housing authorities",
    "nonprofits_non_higher_education_with_501c3": "Nonprofits with 501(c)(3) status",
    "nonprofits_non_higher_education_without_501c3": "Nonprofits without 501(c)(3) status",
    "for_profit_organizations_other_than_small_businesses": "For-profit organizations", "small_businesses": "Small businesses",
    "individuals": "Individuals", "other": "Other (see the eligibility text)", "unrestricted": "Anyone (unrestricted)",
}


def applicants(codes: str) -> str:
    names = [APPLICANT_LABELS.get(c.strip(), c.strip().replace("_", " ")) for c in (codes or "").split(";") if c.strip()]
    return "; ".join(names) or "not stated"


def money(v) -> str:
    if v is None:
        return "not stated"
    return f"${v / 1e6:,.1f}M" if v >= 1e6 else f"${v:,.0f}"


@app.context_processor
def inject():
    ag = current_agency()
    return {"fmt_dt": fmt_dt, "money": money, "applicants": applicants, "refresh_warning": refresh_warning,
            "agency": ag, "agencies": PROFILES, "aid": current_aid(), "TRACKS": TRACKS, "csrf_token": csrf_token,
            "goals": {g["id"]: g for g in ag["strategic_priorities"]},
            "divisions": {d["id"]: d for d in ag["divisions"]}, "run": latest_run()}


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
                            "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; form-action 'self'; "
                            "base-uri 'none'; object-src 'none'; frame-ancestors 'none'")
    if os.getenv("MODE") == "app":   # served only over HTTPS behind Container Apps ingress
        resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    if request.method == "POST" or request.path.endswith(".csv"):
        resp.headers.setdefault("Cache-Control", "no-store")
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
        if r.get("closed_since_refresh"):
            continue
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
    alerts = get_store().read_json(f"alerts/{current_aid()}/latest.json", default={}) or {}
    by_id = {r["id"]: r for r in doc["records"]}
    return render_template("shortlist.html", doc=doc, rows=rows[(page - 1) * PAGE_SIZE: page * PAGE_SIZE], name=session.get("name", ""),
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


def safe_next(nxt: str, fallback: str) -> str:
    """Only same-site relative paths: no scheme, no host, no control characters or backslashes."""
    nxt = nxt or ""
    u = urlsplit(nxt)
    bad = any(c in nxt for c in ("\t", "\r", "\n", "\\"))
    if nxt.startswith("/") and not nxt.startswith("//") and not u.scheme and not u.netloc and not bad:
        return nxt
    return fallback


@app.route("/name", methods=["POST"])
def set_name():
    """Remember who is recording decisions (until Entra ID sign-in replaces this in a pilot)."""
    name = request.form.get("name", "").strip()[:60]
    if name:
        session["name"] = name
        flash(f"Decisions will be recorded as {name}.")
    return redirect(safe_next(request.form.get("next", ""), url_for("shortlist")))


@app.route("/opportunity/<oid>/decision", methods=["POST"])
def decide(oid):
    doc = scored()
    rec = next((r for r in (doc or {}).get("records", []) if r["id"] == oid), None)
    if rec is None:
        abort(404)
    choice = request.form.get("decision", "")
    if choice not in CHOICES:
        abort(400, "Choose Pursue, Maybe or Pass.")
    name = request.form.get("name", "").strip()[:60] or session.get("name", "")
    back = request.form.get("back", "")
    if not name:   # never record an anonymous decision
        flash("Enter your name or initials, then save the decision.")
        return redirect(url_for("detail", oid=oid, back=back or None) + "#dec-h")
    session["name"] = name
    entry = {"decision": choice, "by": name, "note": request.form.get("note", "").strip()[:1000],
             "at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
             "score_at_decision": rec["score"], "confidence_at_decision": rec["confidence"], "run_id": doc["run_id"]}

    def add(cur):
        cur = cur or {"decisions": {}}
        hist = cur.setdefault("decisions", {}).setdefault(oid, [])
        last = hist[-1] if hist else None
        duplicate = bool(last) and all(last.get(k) == entry[k] for k in ("decision", "by", "note")) and (
            datetime.fromisoformat(entry["at"]) - datetime.fromisoformat(last["at"])).total_seconds() < 10
        if not duplicate:        # a double-click or resubmit does not add a second entry
            hist.append(entry)
        return cur
    get_store().update_json(decisions_path(), add, default={"decisions": {}})
    flash(f"Saved: {choice} on “{rec['title'][:80]}”.")
    return redirect(safe_next(request.form.get("next", ""), url_for("detail", oid=oid, back=back or None)))


def cell(v):
    """Spreadsheet-safe cell: text starting with = + - @ (or a tab or CR) gets a leading ' so Excel
    shows it instead of running it as a formula. Numbers stay numbers."""
    if isinstance(v, (int, float)):
        return v
    s = "" if v is None else str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s


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
    w.writerow(["list", "rank", "score", "confidence", "title", "opportunity_number", "funder", "status", "close_date",
                "days_to_close", "award_ceiling", "matched_goal", "matched_objective", "why_it_matches",
                "risk_or_gap", "owning_division", "decision", "decided_by", "decision_note", "grants_gov_link"])
    for r in rows:
        ai = r.get("ai") or {}
        d = (decided.get(r["id"]) or [{}])[-1]
        why = ai.get("why_it_matches") or "; ".join(b["reason"] for b in r["breakdown"][:2])
        w.writerow([cell(x) for x in [TRACKS.get(r["track"], r["track"]), r["rank"], r["score"], r["confidence"], r["title"], r["number"], r["agency"], r["status"],
                    r["close_date"], "" if r["days_to_close"] is None else r["days_to_close"],
                    "" if r["award_ceiling"] is None else int(r["award_ceiling"]),
                    f"{r['matched_goal']['id']} {r['matched_goal']['name']}", r["matched_objective"]["id"], why,
                    ai.get("risk_or_gap", ""), ai.get("owning_division", ""), d.get("decision", ""), d.get("by", ""),
                    d.get("note", ""), r["url"]]])
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
    for g in current_agency()["strategic_priorities"]:
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
    sample = store.read_json(evaluate.sample_path(current_aid()))
    kw = (store.read_json("eval/keyword_baseline/latest.json", default={}) or {}).get("keyword_hits") or {}
    mine = set(current_agency()["profile"]["keywords"])
    kw = {k: v for k, v in kw.items() if k in mine} or None
    m = evaluate.metrics(doc, sample, labels(), decisions(), kw)
    by_id = {r["id"]: r for r in doc["records"]}
    return render_template("evaluation.html", m=m, sample=sample, by_id=by_id, doc=doc)


@app.route("/evaluation/sample", methods=["POST"])
def make_sample():
    doc = scored()
    store = get_store()
    if store.read_json(evaluate.sample_path(current_aid())):
        # Drawn once, never replaced from the web: every label is tied to this sample. To start over,
        # an administrator deletes eval/sample.json and eval/labels.json in storage.
        flash("A sample already exists. Labels are kept with their items.")
        return redirect(url_for("evaluation"))
    store.write_json(evaluate.sample_path(current_aid()), evaluate.draw_sample(doc), indent=2)
    flash("Labeling sample drawn: our top 10, the keyword baseline's top 10, and 10 more from the rest.")
    return redirect(url_for("label"))


@app.route("/evaluation/label", methods=["GET", "POST"])
def label():
    store = get_store()
    sample = store.read_json(evaluate.sample_path(current_aid()))
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
        store.update_json(evaluate.labels_path(current_aid()), lambda cur: {"labels": (cur or {}).get("labels", []) + [entry]},
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
    item = None
    if todo:
        nxt = todo[0]
        # Prefer today's record; fall back to the snapshot taken when the sample was drawn (item closed since).
        item = by_id.get(nxt["id"]) or {"id": nxt["id"], "title": nxt["title"], **(nxt.get("snapshot") or {})}
        item.setdefault("description", "")
        item.setdefault("eligibility", "")
    return render_template("label.html", name=name, item=item, done=len(order) - len(todo), total=len(order))


@app.route("/statewide")
def statewide():
    """The central (OSBM) view: every agency's matches side by side, and opportunities that fit several."""
    rows, strong_by_opp = [], {}
    for prof in PROFILES:
        aid = prof["profile"]["agency_id"]
        doc = scored(aid)
        if not doc:
            continue
        recs = [r for r in doc["records"] if r["track"] == "agency" and not r.get("closed_since_refresh")]
        strong = [r for r in recs if r["confidence"] in ("High", "Medium")]
        dec = decisions(aid)
        latest = [h[-1]["decision"] for h in dec.values() if h]
        for r in strong:
            strong_by_opp.setdefault(r["id"], []).append((prof, r))
        rows.append({"p": prof, "aid": aid, "high": sum(r["confidence"] == "High" for r in recs),
                     "medium": sum(r["confidence"] == "Medium" for r in recs),
                     "closing10": sum(1 for r in strong if r["days_to_close"] is not None and r["days_to_close"] <= 10),
                     "forecast": sum(r["status"] == "forecasted" for r in strong),
                     "pursue": latest.count("Pursue"), "maybe": latest.count("Maybe"), "pass": latest.count("Pass"),
                     "plan": prof["profile"]["plan_title"], "generated": doc.get("generated_at")})
    shared = sorted(([v for v in strong_by_opp.values() if len(v) > 1]),
                    key=lambda v: -max(r["score"] for _, r in v))
    return render_template("statewide.html", rows=rows, shared=shared[:25], n_shared=len(shared))


@app.route("/status")
def status():
    store = get_store()
    runs = []
    for p in sorted(store.list("runs/"), reverse=True):
        if p.endswith(("latest.json", "last_attempt.json")):   # pointers, not runs
            continue
        runs.append(store.read_json(p))
        if len(runs) >= 14:
            break
    doc = scored()
    return render_template("status.html", runs=runs, doc=doc, storage=store.describe())


@app.route("/profile")
def profile():
    return render_template("profile.html", p=get_store().read_json(f"profiles/{current_aid()}.json"))


@app.route("/method")
def method():
    return render_template("method.html", doc=scored())


@app.route("/healthz")
def healthz():
    run = latest_run()
    return {"ok": True, "last_run": (run or {}).get("run_id"), "storage": get_store().kind,
            "agencies": [p["profile"]["agency_id"] for p in PROFILES]}


class _ServerError:
    code = 500
    description = "Something went wrong on our side. Try again in a minute."


@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(405)
def error_page(e):
    return render_template("error.html", e=e), e.code


@app.errorhandler(500)
def server_error(e):
    return render_template("error.html", e=_ServerError()), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")), debug=os.getenv("FLASK_DEBUG") == "1")
