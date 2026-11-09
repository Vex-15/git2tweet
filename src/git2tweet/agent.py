import json
import os
import webbrowser
from typing import Annotated, TypedDict
from urllib.parse import urlencode

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Command, interrupt

from . import repo, store

SYSTEM = """You write tweets for a developer who builds in public.
Look at the recent commits, pick the most tweet-worthy one, read its diff,
then write ONE tweet under 280 characters (first person, casual, max 1 emoji,
max 2 hashtags, never include secrets).
If every commit is trivial (typos, formatting, merges), reply with exactly: SKIP
Output only the tweet text or SKIP."""


@tool
def list_recent_commits(n: int = 3) -> str:
    """List the most recent commits (sha + first line of message)."""
    return json.dumps(repo.list_commits(n))


@tool
def get_commit_diff(sha: str) -> str:
    """Get the full message and code diff for one commit by its sha."""
    return f"Message: {repo.commit_message(sha)}\n\n{repo.commit_diff(sha)}"


TOOLS = [list_recent_commits, get_commit_diff]


class State(TypedDict):
    messages: Annotated[list, add_messages]
    tweet: str
    status: str


def approve(state: State):
    draft = state["messages"][-1].content.strip()
    if draft.strip(" .\"'").upper() == "SKIP":
        return {"status": "skipped"}

    answer = interrupt({"draft": draft, "chars": len(draft)}).strip()

    if answer.lower() == "y":
        return {"tweet": draft, "status": "approved"}
    if answer.lower() == "n":
        return {"status": "rejected"}
    return {"tweet": answer, "status": "approved"}  # anything else = your edit


def post(state: State):
    url = "https://twitter.com/intent/tweet?" + urlencode({"text": state["tweet"]})
    webbrowser.open(url)
    return {"status": "opened"}


def after_approve(state: State):
    return "post" if state["status"] == "approved" else END


def build_graph():
    llm = ChatGroq(
        model=os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
    ).bind_tools(TOOLS)

    def agent(state: State):
        reply = llm.invoke([SystemMessage(SYSTEM)] + state["messages"])
        return {"messages": [reply]}

    builder = StateGraph(State)
    builder.add_node("agent", agent)
    builder.add_node("tools", ToolNode(TOOLS))
    builder.add_node("approve", approve)
    builder.add_node("post", post)

    builder.add_edge(START, "agent")
    builder.add_conditional_edges(
        "agent", tools_condition, {"tools": "tools", END: "approve"}
    )
    builder.add_edge("tools", "agent")
    builder.add_conditional_edges(
        "approve", after_approve, {"post": "post", END: END}
    )
    builder.add_edge("post", END)
    return builder.compile(checkpointer=MemorySaver())


def run(sha: str) -> None:
    if sha in store.load():
        print(f"Already handled {sha[:7]}, skipping.")
        return

    graph = build_graph()
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
        store.mark(sha)
