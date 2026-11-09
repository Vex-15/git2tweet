# Git2Tweet

Turn your git commits into tweet drafts. You approve every one before it goes out.

![demo](docs/demo.gif)

## Install

```bash
pipx install git2tweet     # or: uv tool install git2tweet
git2tweet config           # pick a model provider, paste your API key (once)
```

## Use it

```bash
git commit -m "feat: add retry with backoff to the webhook handler"
git tweet                  # drafts a tweet, you approve or edit, X opens prefilled
```

Want a reminder after every commit? Run `git2tweet init` once per repo.

| Command | What it does |
|---|---|
| `git tweet` / `g2t` | Draft a tweet for your latest commit |
| `git tweet <sha>` | Draft for a specific commit |
| `git tweet --force` | Draft again even if the commit was already handled |
| `git2tweet config` | Set provider, model and API key |
| `git2tweet init` | Install the post-commit reminder hook (`--remove` to undo) |

## How it works

An agent (built with LangGraph) reads your commit and diff, decides if it's worth
sharing, and drafts a tweet. Trivial commits (typos, formatting) are skipped.
You then approve, edit, or reject it. Approved tweets open in X with the text
prefilled, so you press Post yourself. Git2Tweet never holds your X credentials.

## Privacy

- The commit message and diff are sent to the model provider you choose (Groq by default).
- Known secret patterns (API keys, tokens, `password=...`) are redacted first.
  This is best effort, so don't rely on it for sensitive repos.
- For fully local use, pick `ollama` in `git2tweet config`: nothing leaves your machine.
- Git2Tweet sends no telemetry.

## License

MIT

[View full license](https://github.com/Vex-15/git2tweet?tab=MIT-1-ov-file)
