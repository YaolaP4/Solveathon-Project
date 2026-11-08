"""Paths, agency configuration and model settings shared by every layer."""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA = ROOT / "data"
RAW_GRANTS = DATA / "raw" / "grants.csv"
LAYER1_OUTPUT = DATA / "processed" / "grants_features.csv"
RESULTS = DATA / "results"
CACHE = DATA / "cache"            # real model responses, committed so reruns need no API keys
MOCK_RESULTS = RESULTS / "mock"   # mock-mode outputs, never mixed with real ones
MOCK_CACHE = DATA / "cache_mock"

AGENCY_CONFIG = ROOT / "agency" / "priorities.json"
PROMPTS = ROOT / "prompts"

# Models (both reached through the Vercel AI Gateway with one key)
JEV_MODEL = os.getenv("JEV_MODEL", "typesafe-ai/jev")
DEEP_MODEL = os.getenv("DEEP_MODEL", "deepseek/deepseek-v4-pro")
GATEWAY_EVALUATE_URL = "https://ai-gateway.vercel.sh/v1/evaluate"
GATEWAY_CHAT_URL = "https://ai-gateway.vercel.sh/v1/chat/completions"
REQUEST_TIMEOUT_S = 90


def api_key() -> str:
    return os.getenv("AI_GATEWAY_API_KEY", "").strip()


def load_agency() -> dict:
    """The qualifier's agency config (NCDHHS, 2023-2025 plan). The daily matchmaker uses load_profiles()."""
    with open(AGENCY_CONFIG, encoding="utf-8") as f:
        return json.load(f)


PROFILES_DIR = ROOT / "agency" / "profiles"
SHARED_SETTINGS = ("layer1", "layer5_award_history", "matchmaker")


def load_profiles() -> list[dict]:
    """Every agency profile in agency/profiles/*.json (one standard template per agency), NCDHHS first.
    Rule settings that are the same for every agency (Layer 1 rules, award-history window) come from
    agency/priorities.json unless a profile overrides them."""
    base = load_agency()
    out = []
    for path in sorted(PROFILES_DIR.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            prof = json.load(f)
        for key in SHARED_SETTINGS:
            if key not in prof and key in base:
                prof[key] = base[key]
        prof.setdefault("as_of_date", base.get("as_of_date"))
        out.append(prof)
    out.sort(key=lambda p: (p["profile"]["agency_id"] != "ncdhhs", p["profile"]["agency_id"]))
    if not out:
        raise RuntimeError(f"no agency profiles in {PROFILES_DIR}")
    return out


PROMPT_FIELDS = ("agency_name", "mission", "user", "strategic_priorities", "divisions")


def prompt_fields(agency: dict) -> dict:
    """The parts of the agency config that are sent to a model. Only these go into
    the prompt-version hash, so tuning thresholds or Layer 4 weights does not
    invalidate the cache of model answers. Page citations ("source") added to goals for
    the finals profile are not sent to the qualifier's models, so they are left out too."""
    out = {k: agency[k] for k in PROMPT_FIELDS}
    out["strategic_priorities"] = [
        {"id": g["id"], "name": g["name"], "description": g["description"],
         "objectives": [{"id": o["id"], "text": o["text"]} for o in g["objectives"]]}
        for g in agency["strategic_priorities"]]
    return out


def objective_ids(agency: dict) -> set[str]:
    return {o["id"] for p in agency["strategic_priorities"] for o in p["objectives"]}
