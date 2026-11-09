from . import config


def make_llm():
    s = config.get_settings()

    if s["provider"] == "groq":
        from langchain_groq import ChatGroq

        key = config.get_groq_key()
        if not key:
            raise SystemExit("No Groq API key found. Run `git2tweet config` or set GROQ_API_KEY.")
        return ChatGroq(model=s["model"], api_key=key)

    if s["provider"] == "ollama":
        try:
            from langchain_ollama import ChatOllama
        except ImportError:
            raise SystemExit('Ollama support is not installed. Run: pip install "git2tweet[ollama]"')
        return ChatOllama(model=s["model"])

    raise SystemExit(f"Unknown provider '{s['provider']}'. Use groq or ollama.")
