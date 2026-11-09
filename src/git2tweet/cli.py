import argparse
import getpass
import json
import subprocess
import sys

from dotenv import load_dotenv

from . import config, repo

COMMANDS = {"draft", "config"}


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

    # only offer the saved model as default if the provider didn't change
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


def draft(sha: str) -> None:
    from .agent import run  # imported here so `--help` and `config` stay fast

    try:
        full_sha = repo.resolve(sha)
    except (subprocess.CalledProcessError, FileNotFoundError):
        sys.exit("Run this inside a git repository, with a valid commit.")
    run(full_sha)


def main() -> None:
    load_dotenv()  # dev convenience: reads a .env in the current folder

    parser = argparse.ArgumentParser(
        prog="git2tweet",
        description="Turn a git commit into a tweet draft you approve before posting.",
        epilog="Run `git2tweet` alone to draft a tweet for your latest commit.",
    )
    sub = parser.add_subparsers(dest="command", metavar="{draft,config}")

    p_draft = sub.add_parser("draft", help="draft a tweet for a commit (the default)")
    p_draft.add_argument("sha", nargs="?", default="HEAD", help="commit to use (default: latest)")

    p_config = sub.add_parser("config", help="set provider, model and API key")
    p_config.add_argument("--show", action="store_true", help="show current settings")

    argv = sys.argv[1:]
    # `git2tweet` or `git2tweet <sha>` means `git2tweet draft ...`
    if not argv or (argv[0] not in COMMANDS and not argv[0].startswith("-")):
        argv = ["draft", *argv]
    args = parser.parse_args(argv)

    if args.command == "config":
        configure(args.show)
    else:
        draft(args.sha)
