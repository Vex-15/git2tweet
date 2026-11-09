import os
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from gh import list_commits, get_commit, format_diff

llm = ChatGroq(
    model=os.getenv("GROQ_MODEL"),
    temperature=0.7
)

SYSTEM = """You write tweets for a developer who builds in public.
Given a git commit message and diff, write ONE tweet under 280 characters.
First person, casual, say what changed and why it matters.
At most 1 emoji and 2 hashtags. Never include secrets, keys, or tokens.
Output only the tweet text."""

commit = get_commit(list_commits(1)[0]["sha"])
prompt = f"Commit message:\n{commit['commit']['message']}\n\nDiff:\n{format_diff(commit)}"

resp = llm.invoke([SystemMessage(SYSTEM), HumanMessage(prompt)])
tweet = resp.content.strip()
print(tweet)
print(f"\n({len(tweet)} chars)")
