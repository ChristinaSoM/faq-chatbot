import os
import time
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from config import LLM_MODEL, LLM_TEMPERATURE, MAX_HISTORY_MESSAGES, SYSTEM_PROMPT
from logger import get_logger
from tools import TOOLS

load_dotenv()

log = get_logger("graph")

# defines the bot's role and rules.
SYSTEM_MESSAGE = SystemMessage(content=SYSTEM_PROMPT)


def create_llm():
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise ValueError("MISTRAL_API_KEY not found.")
    return init_chat_model(
        LLM_MODEL, temperature=LLM_TEMPERATURE, api_key=api_key
    ).bind_tools(
        TOOLS
    )  # bind_tools registers the available tools with the LLM so it can request them by name


llm = create_llm()
tool_executor = ToolNode(TOOLS)


def assistant_node(state: MessagesState) -> dict:
    # Trim history before sending to stay within a sensible token budget.
    recent_messages = state["messages"][-MAX_HISTORY_MESSAGES:]
    log.info(
        "node=assistant | LLM call | model=%s history_length=%d",
        LLM_MODEL,
        len(recent_messages),
    )
    t0 = time.perf_counter()
    response = llm.invoke([SYSTEM_MESSAGE, *recent_messages])
    log.info("node=assistant | LLM done | elapsed=%.2fs", time.perf_counter() - t0)
    return {"messages": [response]}


def tools_node(state: MessagesState) -> dict:
    names = ", ".join(
        tc["name"] for tc in getattr(state["messages"][-1], "tool_calls", [])
    )
    log.info("node=tools | calling [%s]", names)
    t0 = time.perf_counter()
    result = tool_executor.invoke(state)
    log.info("node=tools | done [%s] elapsed=%.2fs", names, time.perf_counter() - t0)
    return result


def build_graph():
    graph = StateGraph(MessagesState)

    graph.add_node("assistant", assistant_node)
    graph.add_node("tools", tools_node)

    graph.add_edge(START, "assistant")
    # tools_condition routes to "tools" when the LLM emits a tool call, otherwise to END.
    graph.add_conditional_edges("assistant", tools_condition)
    graph.add_edge("tools", "assistant")

    # MemorySaver stores the full conversation in memory so history persists across turns.
    return graph.compile(checkpointer=MemorySaver())
