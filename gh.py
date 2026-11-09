from scrub import scrub
import os

import requests
from dotenv import load_dotenv

load_dotenv(r"F:\Vedant\Projects\AgenticAI\git2tweet\.env")

TOKEN = os.environ["GITHUB_TOKEN"]
OWNER = "Vex-15"
REPO = "Go-shop"
BASE = f"https://api.github.com/repos/{OWNER}/{REPO}/commits"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
}


# 1. list the latest commit
def list_commits(n: int = 3) -> list[dict]:
    r = requests.get(BASE, headers=HEADERS, params={"per_page": n})
    r.raise_for_status()
    return [
        {"sha": c["sha"], "message": c["commit"]["message"].split("\n")[0]}
        for c in r.json()
    ]


# 2. fetch that commit in full (this includes the diff)
def get_commit(sha: str) -> dict:
    r = requests.get(f"{BASE}/{sha}", headers=HEADERS)
    r.raise_for_status()
    return r.json()


def format_diff(commit: dict, max_chars: int = 6000) -> str:
    parts = []
    for f in commit["files"]:
        patch = f.get("patch", "(binary or too large)")
        parts.append(f"--- {f['filename']} ({f['status']})\n{patch}")
    # cap size so the LLM isn't flooded
    return scrub("\n\n".join(parts))[:max_chars]
