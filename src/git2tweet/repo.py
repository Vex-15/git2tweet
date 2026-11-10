import subprocess
from pathlib import Path

from .scrub import scrub

# Files whose diffs are never sent to the model.
SENSITIVE_GLOBS = [
    ".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx",
    "id_rsa*", "id_ed25519*", ".npmrc", ".pypirc", "*.tfstate",
]


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        check=True,
    )
    return result.stdout.strip()


def resolve(ref: str = "HEAD") -> str:
    """Turn HEAD, a short sha, or a branch name into a full sha."""
    return _git("rev-parse", ref)


def list_commits(n: int = 3) -> list[dict]:
    out = _git("log", f"-{n}", "--pretty=format:%H%x09%s")
    rows = [line.partition("\t") for line in out.splitlines()]
    return [{"sha": sha, "message": scrub(msg)} for sha, _, msg in rows]


def commit_message(sha: str) -> str:
    return scrub(_git("show", "-s", "--format=%B", sha))


def commit_diff(sha: str, max_chars: int = 6000) -> str:
    excludes = [f":(exclude,glob)**/{g}" for g in SENSITIVE_GLOBS]
    patch = _git("show", "--format=", "--patch", sha, "--", ".", *excludes)
    if not patch.strip():
        return "(no diff to show: empty commit, or only files hidden for privacy)"
    return scrub(patch)[:max_chars]


def git_dir() -> Path:
    """The repo's .git folder (works from any subfolder, worktrees too)."""
    return Path(_git("rev-parse", "--absolute-git-dir"))


def hooks_dir() -> Path:
    """Where this repo's hooks live (respects a custom core.hooksPath)."""
    return Path(_git("rev-parse", "--git-path", "hooks")).resolve()


def is_merge(sha: str) -> bool:
    parts = _git("rev-list", "--parents", "-n", "1", sha).split()
    return len(parts) > 2  # sha + 2 or more parents
