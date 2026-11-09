import re

PATTERNS = [
    r"ghp_[A-Za-z0-9]{36}",
    r"github_pat_[A-Za-z0-9_]{20,}",
    r"gsk_[A-Za-z0-9]{20,}",
    r"sk-[A-Za-z0-9_-]{20,}",
    r"AKIA[0-9A-Z]{16}",
    r"(?i)(api[_-]?key|token|secret|password)\s*[=:]\s*\S+",
]


def scrub(text: str) -> str:
    for p in PATTERNS:
        text = re.sub(p, "[REDACTED]", text)
    return text
