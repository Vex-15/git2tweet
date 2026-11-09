import uuid
import json
import os
from typing import Annotated, TypedDict
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from gh import list_commits, get_commit, format_diff
import webbrowser
from urllib.parse import urlencode
from langgraph.graph import END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import MemorySaver
import sys
import store

# 1. Tools: the docstring is what the model reads to decide when to use it


@tool
def list_recent_commits(n: int = 3) -> str:
    """List the most recent commits (sha + first line of message)."""
    return json.dumps(list_commits(n))


@tool
def get_commit_diff(sha: str) -> str:
    """Get the full message and code diff for one commit by its sha."""
    c = get_commit(sha)
    return f"Message: {c['commit']['message']}\n\n{format_diff(c)}"


tools = [list_recent_commits, get_commit_diff]
llm = ChatGroq(model=os.environ.get(
    "GROQ_MODEL", "llama-3.3-70b-versatile")).bind_tools(tools)

SYSTEM = """You write tweets for a developer who builds in public.
Look at the recent commits, pick the most tweet-worthy one, read its diff,
then write ONE tweet under 280 characters (first person, casual, max 1 emoji,
max 2 hashtags, never include secrets).
If every commit is trivial (typos, formatting, merges), reply with exactly: SKIP
Output only the tweet text or SKIP."""


# 2. State: what the graph carries between steps
class State(TypedDict):
    messages: Annotated[list, add_messages]
    tweet: str
    status: str


# 3. Node: one LLM call
def agent(state: State):
    reply = llm.invoke([SystemMessage(SYSTEM)] + state["messages"])
    return {"messages": [reply]}


def approve(state: State):
    draft = state["messages"][-1].content.strip()
    if draft == "SKIP":
        return {"status": "SKIP"}

    answer = interrupt({"draft": draft, "chars": len(draft)}).strip()

    if answer.lower() == "y":
        return {"tweet": draft, "status": "approved"}
    if answer.lower() == "n":
        return {"status": "rejected"}

    # anything else = your edited version
    return {"tweet": answer, "status": "approved"}


def post(state: State):
    url = "https://twitter.com/intent/tweet?" + \
        urlencode({"text": state["tweet"]})
    webbrowser.open(url)    # opens X with the tweet prefilled, you press Post
    return {"status": "opened"}


def after_approve(state: State):
    return "post" if state["status"] == "approved" else END


# 4. Wire the graph
builder = StateGraph(State)
builder.add_node("agent", agent)
builder.add_node("tools", ToolNode(tools))
builder.add_node("approve", approve)
builder.add_node("post", post)

builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", tools_condition, {
                              "tools": "tools", END: "approve"})
builder.add_edge("tools", "agent")
builder.add_conditional_edges("approve", after_approve, {
                              "post": "post", END: END})
builder.add_edge("post", END)

graph = builder.compile(checkpointer=MemorySaver())

# which commit? CLI arg, or fall back to the latest
sha = sys.argv[1] if len(sys.argv) > 1 else list_commits(1)[0]["sha"]

if sha in store.load():
    print(f"Already handled {sha[:7]}, skipping.")
    sys.exit(0)

config = {"configurable": {"thread_id": sha}, "recursion_limit": 10}
task = f"Write a tweet about commit {sha}. Read its diff with get_commit_diff first."

result = graph.invoke({"messages": [HumanMessage(task)]}, config)

while "__interrupt__" in result:
    info = result["__interrupt__"][0].value
    print(f"\nDRAFT ({info['chars']} chars):\n{info['draft']}\n")
    answer = input("Post? [y] yes / [n] no / or type your edited tweet: ")
    result = graph.invoke(Command(resume=answer), config)

status = result["status"]
print("Status:", status)

if status == "opened":
    if input("Did you press Post on X? [y/n] ").lower() == "y":
        store.mark(sha)
elif status in ("skipped", "rejected"):
    store.mark(sha)    # decided not to tweet it, don't ask again
