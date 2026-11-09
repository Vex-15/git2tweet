import stat

from . import repo

MARKER_START = "# >>> git2tweet >>>"
MARKER_END = "# <<< git2tweet <<<"
BLOCK = (
    f"{MARKER_START}\n"
    "command -v git2tweet >/dev/null 2>&1 && git2tweet hook || true\n"
    f"{MARKER_END}\n"
)


def _path():
    return repo.hooks_dir() / "post-commit"


def install() -> str:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        text = path.read_text(encoding="utf-8")
        if MARKER_START in text:
            return f"Already installed ({path})"
        first = text.splitlines()[0] if text else ""
        if not (first.startswith("#!") and first.rstrip().endswith("sh")):
            return "A non-shell post-commit hook already exists. Add `git2tweet hook` to it manually."
        text = text.rstrip("\n") + "\n\n" + BLOCK
    else:
        text = "#!/bin/sh\n\n" + BLOCK

    path.write_text(text, encoding="utf-8", newline="\n")  # LF only, or sh breaks on Windows
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return f"Installed post-commit hook ({path})"


def remove() -> str:
    path = _path()
    if not path.exists():
        return "No git2tweet hook found."
    text = path.read_text(encoding="utf-8")
    if MARKER_START not in text:
        return "No git2tweet hook found."

    start = text.index(MARKER_START)
    end = text.index(MARKER_END) + len(MARKER_END)
    rest = (text[:start] + text[end:]).strip()

    if rest in ("", "#!/bin/sh"):
        path.unlink()  # the hook was only ours, so delete the file
    else:
        path.write_text(rest + "\n", encoding="utf-8", newline="\n")
    return "Removed git2tweet hook."
