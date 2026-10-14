from langchain_core.messages import HumanMessage
from graph import build_graph
from config import WELCOME_TEXT

SEPARATOR = "─" * 100


def print_section(label: str, text: str) -> None:
    print(f"\n{label}\n{text}\n{SEPARATOR}")


def run_chatbot() -> None:
    try:
        graph = build_graph()
    except RuntimeError as exc:
        print(f"Startup error: {exc}")
        return

    # thread_id groups all messages of this session so MemorySaver can retrieve the full history
    config = {"configurable": {"thread_id": "session"}}
    print(f"{SEPARATOR}\n{WELCOME_TEXT}\n{SEPARATOR}")

    while True:
        user_input = input("\nSie: ").strip()

        if user_input.lower() == "exit":
            break

        try:
            result = graph.invoke(
                {"messages": [HumanMessage(content=user_input)]},
                config,
            )
            print_section("Assistent:", result["messages"][-1].content)
        except Exception as exc:
            print_section(
                "Assistent:",
                f"Entschuldigung, es ist ein Fehler aufgetreten ({exc}). Bitte versuchen Sie es später noch einmal.",
            )


if __name__ == "__main__":
    run_chatbot()
