import argparse
import getpass
import json
import subprocess
import sys

from dotenv import load_dotenv

from . import config, hooks, repo, store

COMMANDS = {"draft", "config", "init"}


def route(argv: list[str]) -> list[str]:
    """`git2tweet` or `git2tweet <sha> [flags]` means `git2tweet draft ...`."""
    if not argv or (argv[0] not in COMMANDS and argv[0] not in ("-h", "--help")):
        return ["draft", *argv]
    return argv


def configure(show: bool) -> None:
    cfg = config.load()

    if show:
        shown = dict(cfg)
        if "groq_api_key" in shown:
            shown["groq_api_key"] = "****" + shown["groq_api_key"][-4:]
        print(json.dumps(shown, indent=2))
        print(f"\nConfig file: {config.CONFIG_FILE}")
        return

    current = cfg.get("provider", "groq")
    provider = input(f"Provider [groq/ollama] ({current}): ").strip().lower() or current
    if provider not in config.DEFAULT_MODELS:
        sys.exit(f"Unknown provider '{provider}'. Choose: {', '.join(config.DEFAULT_MODELS)}")

    default_model = (cfg.get("model") if provider == cfg.get("provider") else None) \
        or config.DEFAULT_MODELS[provider]
    cfg["provider"] = provider
    cfg["model"] = input(f"Model ({default_model}): ").strip() or default_model

    if provider == "groq":
        key = getpass.getpass("Groq API key (hidden, Enter keeps current): ").strip()
        if key:
            cfg["groq_api_key"] = key

    config.save(cfg)
    print(f"Saved to {config.CONFIG_FILE}")


def draft(sha: str, force: bool = False, no_skip: bool = False) -> None:
    from .agent import run  # imported here so --help, config and hook stay fast

    try:
        full_sha = repo.resolve(sha)
    except (subprocess.CalledProcessError, FileNotFoundError):
        sys.exit("Run this inside a git repository, with a valid commit.")
    run(full_sha, force or no_skip, no_skip)  # --no-skip also bypasses "already handled"


def init(remove: bool) -> None:
    try:
        msg = hooks.remove() if remove else hooks.install()
    except (subprocess.CalledProcessError, FileNotFoundError):
        sys.exit("Run this inside a git repository.")
    print(msg)
    if msg.startswith("Installed"):
        print("After each commit you'll see a reminder. Run `git tweet` to draft a tweet.")


def hook() -> None:
    """Called by the post-commit hook: must be fast, quiet, and never fail."""
    try:
        sha = repo.resolve("HEAD")
        if sha in store.load() or repo.is_merge(sha):
            return
        subject = repo.list_commits(1)[0]["message"]
        print(f"git2tweet: tweet this? Run `git tweet` ({sha[:7]}: {subject})")
    except Exception:
        pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="git2tweet",
        description="Turn a git commit into a tweet draft you approve before posting.",
        epilog="Run `git2tweet` alone to draft a tweet for your latest commit.",
    )
    sub = parser.add_subparsers(dest="command", metavar="{draft,config,init}")

    p_draft = sub.add_parser("draft", help="draft a tweet for a commit (the default)")
    p_draft.add_argument("sha", nargs="?", default="HEAD", help="commit to use (default: latest)")
    p_draft.add_argument("--force", action="store_true",
                         help="draft again even if this commit was already handled")
    p_draft.add_argument("--no-skip", action="store_true",
                         help="draft a tweet even if the commit looks trivial")

    p_config = sub.add_parser("config", help="set provider, model and API key")
    p_config.add_argument("--show", action="store_true", help="show current settings")

    p_init = sub.add_parser("init", help="install a git hook that reminds you after each commit")
    p_init.add_argument("--remove", action="store_true", help="uninstall the hook")
    return parser


def main() -> None:
    load_dotenv()  # dev convenience: reads a .env in the current folder

    argv = sys.argv[1:]
    if argv[:1] == ["hook"]:  # internal command used by the post-commit hook
        hook()
        return

    args = build_parser().parse_args(route(argv))

    try:
        if args.command == "config":
            configure(args.show)
        elif args.command == "init":
            init(args.remove)
        else:
            draft(args.sha, args.force, args.no_skip)
    except (KeyboardInterrupt, EOFError):
        sys.exit("\nCancelled.")
