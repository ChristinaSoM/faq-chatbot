import os

# Must be set before graph.py is imported, because graph.py calls create_llm() at module level.
os.environ.setdefault("MISTRAL_API_KEY", "test-key")
