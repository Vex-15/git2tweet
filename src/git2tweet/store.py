import json

from . import repo


def _file():
    return repo.git_dir() / "git2tweet.json"


def load() -> set[str]:
    f = _file()
    if not f.exists():
        return set()
    try:
        return set(json.loads(f.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, TypeError):
        return set()


def mark(sha: str) -> None:
    shas = load()
    shas.add(sha)
    _file().write_text(json.dumps(sorted(shas)), encoding="utf-8")
