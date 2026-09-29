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
DEEP_MODEL = os.getenv("DEEP_MODEL", "meta/muse-spark-1.3-contributor")
GATEWAY_EVALUATE_URL = "https://ai-gateway.vercel.sh/v1/evaluate"
GATEWAY_CHAT_URL = "https://ai-gateway.vercel.sh/v1/chat/completions"
REQUEST_TIMEOUT_S = 90


def api_key() -> str:
    return os.getenv("AI_GATEWAY_API_KEY", "").strip()


def load_agency() -> dict:
    with open(AGENCY_CONFIG, encoding="utf-8") as f:
        return json.load(f)


def objective_ids(agency: dict) -> set[str]:
    return {o["id"] for p in agency["strategic_priorities"] for o in p["objectives"]}
