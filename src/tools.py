import json
from langchain_core.tools import tool
from config import FAQ_FILE


@tool("get_faqs", description="Returns the list of FAQs.")
def get_faqs() -> list:
    try:
        faqs = json.loads(FAQ_FILE.read_text(encoding="utf-8"))
        # Strip the id field so the LLM never references entries by number ("FAQ 6")
        return [{"question": f["question"], "answer": f["answer"]} for f in faqs]
    except FileNotFoundError:
        return f"ERROR: FAQ file not found at {FAQ_FILE}."


TOOLS = [get_faqs]
