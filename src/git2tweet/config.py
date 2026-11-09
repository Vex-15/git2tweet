import json
import os
from pathlib import Path

from platformdirs import user_config_dir

CONFIG_FILE = Path(user_config_dir("git2tweet")) / "config.json"

DEFAULT_MODELS = {
    "groq": "openai/gpt-oss-120b",
    "ollama": "llama3.1",
}


def load() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save(cfg: dict) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    try:
        CONFIG_FILE.chmod(0o600)  # owner-only on Mac/Linux
    except OSError:
        pass


def get_settings() -> dict:
    """Environment variables win over the config file, which wins over defaults."""
    cfg = load()
    provider = os.environ.get("GIT2TWEET_PROVIDER") or cfg.get("provider", "groq")
    model = (
        os.environ.get("GIT2TWEET_MODEL")
        or cfg.get("model")
        or DEFAULT_MODELS.get(provider, "")
    )
    return {"provider": provider, "model": model}


def get_groq_key() -> str | None:
    return os.environ.get("GROQ_API_KEY") or load().get("groq_api_key")
