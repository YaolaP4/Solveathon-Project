"""Azure OpenAI access for the daily job: embeddings (semantic match) and one chat model (rationales).

Configured with environment variables (Container Apps secrets in Azure, .env on a laptop):
    AOAI_ENDPOINT            https://<name>.openai.azure.com/
    AOAI_KEY                 key (secret)
    AOAI_EMBED_DEPLOYMENT    deployment name of text-embedding-3-small (default "embed")
    AOAI_CHAT_DEPLOYMENT     deployment name of the chat model (default "chat")
    AOAI_API_VERSION         default 2024-10-21

If AOAI_ENDPOINT/AOAI_KEY are missing, `available()` is False and the job falls back to
TF-IDF matching and skips AI summaries. The app still works; it says so on screen.
"""

import os
import time

EMBED_DIMENSIONS = 512          # text-embedding-3-small supports shortened vectors; 512 keeps storage small
EMBED_BATCH = 64
MAX_EMBED_CHARS = 6000


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def available() -> bool:
    return bool(_env("AOAI_ENDPOINT") and _env("AOAI_KEY"))


def chat_deployment() -> str:
    return _env("AOAI_CHAT_DEPLOYMENT", "chat")


def chat_model_name() -> str:
    """The model behind the chat deployment, for display (deployment names are arbitrary)."""
    return _env("AOAI_CHAT_MODEL", "gpt-4.1-mini")


def embed_deployment() -> str:
    return _env("AOAI_EMBED_DEPLOYMENT", "embed")


_client = None


def client():
    global _client
    if _client is None:
        from openai import AzureOpenAI
        _client = AzureOpenAI(azure_endpoint=_env("AOAI_ENDPOINT"), api_key=_env("AOAI_KEY"),
                              api_version=_env("AOAI_API_VERSION", "2024-10-21"), max_retries=5, timeout=120)
    return _client


def embed(texts: list[str]) -> list[list[float]]:
    out: list[list[float]] = []
    for i in range(0, len(texts), EMBED_BATCH):
        batch = [(t or " ")[:MAX_EMBED_CHARS] for t in texts[i:i + EMBED_BATCH]]
        for attempt in range(5):
            try:
                resp = client().embeddings.create(model=embed_deployment(), input=batch, dimensions=EMBED_DIMENSIONS)
                out += [d.embedding for d in sorted(resp.data, key=lambda d: d.index)]
                break
            except Exception:
                if attempt == 4:
                    raise
                time.sleep(2 ** attempt)
    return out


def chat_json(system: str, user: str, max_tokens: int = 1200) -> tuple[str, dict]:
    """One JSON-mode chat completion. Returns (content, usage)."""
    kwargs = dict(model=chat_deployment(), response_format={"type": "json_object"},
                  messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
    try:
        resp = client().chat.completions.create(temperature=0, max_tokens=max_tokens, **kwargs)
    except Exception as e:  # reasoning models reject temperature / max_tokens
        if "temperature" in str(e) or "max_tokens" in str(e) or "unsupported" in str(e).lower():
            resp = client().chat.completions.create(max_completion_tokens=max_tokens * 4, **kwargs)
        else:
            raise
    usage = {"prompt_tokens": resp.usage.prompt_tokens, "completion_tokens": resp.usage.completion_tokens} if resp.usage else {}
    return resp.choices[0].message.content or "", usage
