import json
import os
from unittest.mock import patch

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage

import graph as graph_module
import tools
from config import MAX_HISTORY_MESSAGES
from graph import assistant_node, build_graph, create_llm

FAQ_DATA = [
    {"id": 1, "question": "Was bieten Sie an?", "answer": "Wir bieten IT-Services an."},
]

# Simulates the LLM deciding to call the get_faqs tool.
TOOL_CALL_MESSAGE = AIMessage(
    content="",
    tool_calls=[{"name": "get_faqs", "args": {}, "id": "call_1", "type": "tool_call"}],
)


@pytest.fixture
def faq_file(tmp_path):
    path = tmp_path / "faqs.json"
    path.write_text(json.dumps(FAQ_DATA), encoding="utf-8")
    return path


class TestCreateLlm:
    def test_raises_when_api_key_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MISTRAL_API_KEY", None)
            with pytest.raises(ValueError, match="MISTRAL_API_KEY"):
                create_llm()


class TestAssistantNode:
    def test_returns_ai_message_with_correct_content(self):
        fake_llm = GenericFakeChatModel(messages=iter([AIMessage(content="Hallo!")]))
        with patch.object(graph_module, "llm", fake_llm):
            result = assistant_node({"messages": [HumanMessage(content="Hallo")]})
        assert result["messages"][0].content == "Hallo!"

    def test_trims_history_to_max_messages(self):
        """LLM must only receive the last MAX_HISTORY_MESSAGES, not the full history."""
        from unittest.mock import MagicMock

        many_messages = [HumanMessage(content=f"Frage {i}") for i in range(MAX_HISTORY_MESSAGES + 5)]
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content="Antwort")

        with patch.object(graph_module, "llm", mock_llm):
            assistant_node({"messages": many_messages})

        # First arg to llm.invoke is [SYSTEM_MESSAGE, *recent_messages]
        called_with = mock_llm.invoke.call_args[0][0]
        assert len(called_with) == MAX_HISTORY_MESSAGES + 1  # +1 for SYSTEM_MESSAGE


class TestFullGraph:
    def test_returns_direct_answer_without_tool_call(self):
        """When the LLM answers directly (e.g. a greeting), the tools node is never reached."""
        fake_llm = GenericFakeChatModel(messages=iter([
            AIMessage(content="Hallo! Wie kann ich helfen?"),
        ]))
        with patch.object(graph_module, "llm", fake_llm):
            compiled = build_graph()
            result = compiled.invoke(
                {"messages": [HumanMessage(content="Hallo")]},
                config={"configurable": {"thread_id": "test-direct"}},
            )
        assert result["messages"][-1].content == "Hallo! Wie kann ich helfen?"
        # Only HumanMessage + AIMessage — no ToolMessage in between.
        assert len(result["messages"]) == 2

    def test_returns_answer_after_tool_call(self, faq_file):
        fake_llm = GenericFakeChatModel(messages=iter([
            TOOL_CALL_MESSAGE,
            AIMessage(content="Wir bieten IT-Services an."),
        ]))
        with patch.object(graph_module, "llm", fake_llm), \
             patch.object(tools, "FAQ_FILE", faq_file):
            compiled = build_graph()
            result = compiled.invoke(
                {"messages": [HumanMessage(content="Was bieten Sie an?")]},
                config={"configurable": {"thread_id": "test-tool"}},
            )
        assert result["messages"][-1].content == "Wir bieten IT-Services an."

    def test_memory_persists_across_turns(self, faq_file):
        """After a repeated question the full message history from the first turn is present."""
        fake_llm = GenericFakeChatModel(messages=iter([
            TOOL_CALL_MESSAGE,
            AIMessage(content="Wir bieten IT-Services an."),
            AIMessage(content="Wie bereits erwähnt: Wir bieten IT-Services an."),
        ]))
        config = {"configurable": {"thread_id": "test-memory"}}
        with patch.object(graph_module, "llm", fake_llm), \
             patch.object(tools, "FAQ_FILE", faq_file):
            compiled = build_graph()
            compiled.invoke(
                {"messages": [HumanMessage(content="Was bieten Sie an?")]},
                config=config,
            )
            result = compiled.invoke(
                {"messages": [HumanMessage(content="Was bieten Sie an?")]},
                config=config,
            )
        # Turn 1: HumanMessage, ToolCallMessage, ToolMessage, AIMessage (4)
        # Turn 2 adds: HumanMessage, AIMessage (2) → total 6
        assert len(result["messages"]) == 6
        assert result["messages"][-1].content == "Wie bereits erwähnt: Wir bieten IT-Services an."
