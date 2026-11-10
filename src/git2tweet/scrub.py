import re

# Specific, well-known key formats first; the generic assignment rule last.
PATTERNS = [
    r"ghp_[A-Za-z0-9]{36}",
    r"github_pat_[A-Za-z0-9_]{20,}",
    r"gsk_[A-Za-z0-9]{20,}",
    r"sk-[A-Za-z0-9_-]{20,}",
    r"[sr]k_(?:live|test)_[A-Za-z0-9]{16,}",  # Stripe
    r"AKIA[0-9A-Z]{16}",  # AWS access key id
    r"AIza[0-9A-Za-z_-]{35}",  # Google API key
    r"xox[abprs]-[A-Za-z0-9-]{10,}",  # Slack
    r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",  # JWT
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----",
    r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{16,}",
    r"(?<=://)[^/\s:@]+:[^/\s@]+(?=@)",  # user:password@ in connection URLs
    r"(?i)(api[_-]?key|secret|password|passwd|token)[\"']?\s*[=:]\s*[\"']?[^\s\"',;]{6,}",
]


def scrub(text: str) -> str:
    for p in PATTERNS:
        text = re.sub(p, "[REDACTED]", text)
    return text
