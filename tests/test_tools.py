import json
from unittest.mock import patch

import pytest

import tools
from tools import get_faqs

FAQ_DATA = [
    {"id": 1, "question": "Was bieten Sie an?", "answer": "Wir bieten IT-Services an."},
    {"id": 2, "question": "Welche Support-Optionen gibt es?", "answer": "24/7 Helpdesk-Support."},
]


@pytest.fixture
def faq_file(tmp_path):
    path = tmp_path / "faqs.json"
    path.write_text(json.dumps(FAQ_DATA), encoding="utf-8")
    return path


class TestGetFaqs:
    def test_returns_list(self, faq_file):
        with patch.object(tools, "FAQ_FILE", faq_file):
            result = get_faqs.invoke({})
        assert isinstance(result, list)
        assert len(result) == len(FAQ_DATA)

    def test_strips_id_field(self, faq_file):
        with patch.object(tools, "FAQ_FILE", faq_file):
            result = get_faqs.invoke({})
        assert all("id" not in entry for entry in result)

    def test_returns_question_and_answer(self, faq_file):
        with patch.object(tools, "FAQ_FILE", faq_file):
            result = get_faqs.invoke({})
        assert result[0]["question"] == FAQ_DATA[0]["question"]
        assert result[0]["answer"] == FAQ_DATA[0]["answer"]

    def test_empty_faq_file_returns_empty_list(self, tmp_path):
        path = tmp_path / "faqs.json"
        path.write_text("[]", encoding="utf-8")
        with patch.object(tools, "FAQ_FILE", path):
            result = get_faqs.invoke({})
        assert result == []

    def test_missing_file_returns_error_string(self, tmp_path):
        with patch.object(tools, "FAQ_FILE", tmp_path / "missing.json"):
            result = get_faqs.invoke({})
        assert isinstance(result, str)
        assert "ERROR" in result
