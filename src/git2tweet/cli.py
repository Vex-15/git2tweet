import argparse
import os
import subprocess
import sys

from dotenv import load_dotenv

from . import repo
from .agent import run


def main() -> None:
    load_dotenv()  # picks up a .env in the current folder, if there is one

    parser = argparse.ArgumentParser(
        prog="git2tweet",
        description="Turn a git commit into a tweet draft.",
    )
    parser.add_argument("sha", nargs="?", default="HEAD",
                        help="commit to tweet about (default: latest)")
    args = parser.parse_args()

    if not os.environ.get("GROQ_API_KEY"):
        sys.exit("GROQ_API_KEY is not set. Put it in a .env file or your environment.")

    try:
        sha = repo.resolve(args.sha)
    except (subprocess.CalledProcessError, FileNotFoundError):
        sys.exit("Run this inside a git repository, with a valid commit.")

    run(sha)
