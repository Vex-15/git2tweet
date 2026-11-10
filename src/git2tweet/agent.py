import json
import webbrowser
from typing import Annotated, TypedDict
from urllib.parse import urlencode

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Command, interrupt

from . import repo, store
from .llm import make_llm

SYSTEM = """You write tweets for a developer who builds in public.
Look at the recent commits, pick the most tweet-worthy one, read its diff,
then write ONE tweet under 280 characters (first person, casual, max 1 emoji,
max 2 hashtags, never include secrets).
If every commit is trivial (typos, formatting, tiny test edits, merges), reply with
exactly: SKIP: <reason in under 10 words>
Output only the tweet text or the SKIP line."""


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
    reason: str


def _text(message) -> str:
    """Message text as a plain string (some providers return a list of parts)."""
    content = message.content
    if isinstance(content, list):
        content = "".join(
            part if isinstance(part, str) else part.get("text", "") for part in content
        )
    return content.strip()


def approve(state: State):
    draft = _text(state["messages"][-1])
    if draft.upper().startswith("SKIP:") or draft.strip(" .\"'").upper() == "SKIP":
        reason = draft.split(":", 1)[1].strip() if ":" in draft else ""
        return {"status": "skipped", "reason": reason}

    answer = interrupt({"draft": draft, "chars": len(draft)}).strip()

    if not answer:  # just pressing Enter cancels; it never posts an empty tweet
        return {"status": "cancelled"}

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
    llm = make_llm().bind_tools(TOOLS)

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


def run(sha: str, force: bool = False, no_skip: bool = False) -> None:
    if not force and sha in store.load():
        print(f"Already handled {sha[:7]}, skipping.")
        return

    graph = build_graph()
    config = {"configurable": {"thread_id": sha}, "recursion_limit": 10}
    task = f"Write a tweet about commit {sha}. Read its diff with get_commit_diff first."
    if no_skip:
        task += " Never reply SKIP; write the best tweet you can even if the change is small."

    result = graph.invoke({"messages": [HumanMessage(task)]}, config)

    while "__interrupt__" in result:
        info = result["__interrupt__"][0].value
        print(f"\nDRAFT ({info['chars']} chars):\n{info['draft']}\n")
        while True:
            answer = input("Post? [y]es / [n]o (don't ask again) / Enter to cancel / or type an edit: ").strip()
            if answer.lower() in ("y", "n", "") or len(answer) <= 280:
                break
            print(f"That edit is {len(answer)} characters (the limit is 280). Try again.")
        result = graph.invoke(Command(resume=answer), config)

    status = result["status"]
    if status == "skipped":
        print(f"Skipped: {result.get('reason') or 'it looked too small to tweet about'}.")
        print("Run `git tweet --no-skip` to draft it anyway.")
    elif status == "cancelled":
        print("Cancelled. Nothing was posted.")
    else:
        print("Status:", status)

    if status == "opened":
        if input("Did you press Post on X? [y/n] ").lower() == "y":
            store.mark(sha)
    elif status in ("skipped", "rejected"):
        store.mark(sha)
