"""API clients for Jev (Layer 2) and the deep-analysis chat model (Layer 3).

Both go through the Vercel AI Gateway with one key (AI_GATEWAY_API_KEY in .env).
The Mock* clients let anyone dry-run the pipeline without a key; their outputs are
fake and are written to separate folders (data/cache_mock, data/results/mock).
"""

import json
import re
import time

import requests

import config


class APIError(RuntimeError):
    pass


def _post(url: str, body: dict, retries: int = 4) -> dict:
    key = config.api_key()
    if not key:
        raise APIError("AI_GATEWAY_API_KEY is not set (copy .env.example to .env), "
                       "or run with --mock for a dry run.")
    headers = {"Authorization": f"Bearer {key}"}
    for attempt in range(retries):
        r = requests.post(url, headers=headers, json=body, timeout=config.REQUEST_TIMEOUT_S)
        if r.status_code == 200:
            return r.json()
        if r.status_code in (429, 500, 502, 503, 504) and attempt < retries - 1:
            time.sleep(2 ** attempt)
            continue
        raise APIError(f"HTTP {r.status_code} from {url}: {r.text[:200]}")
    raise APIError("unreachable")


class JevClient:
    """Jev answers typed `choice` questions about a `state` and returns, for each
    question, the chosen option plus a probability for every option."""

    model = config.JEV_MODEL

    def evaluate(self, state: dict, questions: dict) -> dict:
        data = _post(config.GATEWAY_EVALUATE_URL,
                     {"model": self.model, "state": state, "questions": questions})
        return data.get("answers") or data.get("results") or {}


class ChatClient:
    """OpenAI-compatible chat completions through the gateway."""

    model = config.DEEP_MODEL

    def complete(self, messages: list[dict]) -> str:
        data = _post(config.GATEWAY_CHAT_URL,
                     {"model": self.model, "messages": messages, "temperature": 0})
        return data["choices"][0]["message"]["content"]


# ── Mock clients (dry runs only; outputs are NOT real model judgments) ─────────

class MockJevClient:
    model = "mock-jev"

    def evaluate(self, state: dict, questions: dict) -> dict:
        text = " ".join(str(v) for v in state.get("grant", {}).values()).lower()
        health = len(re.findall(r"health|medicaid|behavioral|substance|child|maternal|aging|disabilit", text))
        answers = {}
        for name, q in questions.items():
            options = list(q["criteria"])
            # Put most mass on one option picked from a simple keyword count.
            if name == "domain_relevance":
                pick = options[min(health, len(options) - 1)]
            else:
                pick = options[(len(text) + len(name)) % len(options)]
            rest = (1 - 0.7) / max(len(options) - 1, 1)
            answers[name] = {"choice": pick,
                             "probabilities": {o: (0.7 if o == pick else rest) for o in options}}
        return answers


class MockChatClient:
    model = "mock-chat"

    def complete(self, messages: list[dict]) -> str:
        user = messages[-1]["content"]
        m = re.search(r"ELIGIBILITY TEXT:\n(.{20,80}?)[.\n]", user)
        quote = m.group(1).strip() if m else ""
        return json.dumps({
            "strategic_alignment": 5, "matched_goal": "G1", "matched_objective": "G1.O3",
            "strategic_reason": "MOCK output - not a real judgment.",
            "strategic_evidence_quote": quote,
            "applicant_role": "unclear", "eligibility_evidence_quote": quote,
            "owning_division": "OSEC",
            "operational_fit": 5, "operational_reason": "MOCK",
            "restrictions": [], "major_risk": "MOCK",
            "recommended_for_review": False,
            "one_line_rationale": "MOCK output - run without --mock for real results.",
        })
