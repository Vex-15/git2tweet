import json
import pathlib

FILE = pathlib.Path("posted.json")


def load() -> set[str]:
    return set(json.loads(FILE.read_text())) if FILE.exists() else set()


def mark(sha: str) -> None:
    shas = load()
    shas.add(sha)
    FILE.write_text(json.dumps(sorted(shas)))
