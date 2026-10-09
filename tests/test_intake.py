import pytest

from underwriting.agents.intake import intake_agent, profile_from_raw
from underwriting.fixtures import APP_1001, APP_1005
from underwriting.llm import LLM


class FakeLLM:
    def __init__(self, content):
        self.content = content

    def complete(self, agent, system, user):
        return {"content": self.content, "usage": {"input": 0, "output": 0, "total": 0}}


def test_complete_profile():
    profile = intake_agent(APP_1001, LLM())
    assert profile["applicant_id"] == "APP-1001"
    assert profile["full_name"] == "Alice Chen"
    assert profile["product"] == "homeowners"
    assert profile["complete"] is True
    assert profile["missing_fields"] == []


def test_missing_product():
    profile = intake_agent(APP_1005, LLM())
    assert profile["complete"] is False
    assert "product" in profile["missing_fields"]


def test_nonsense_field_is_dropped():
    raw = dict(APP_1001, favorite_color="blue")
    profile = intake_agent(raw, LLM())
    assert "favorite_color" not in profile


def test_returns_matching_model_reply():
    expected = profile_from_raw(APP_1001)
    assert intake_agent(APP_1001, FakeLLM(expected)) == expected


def test_wrong_profile_raises():
    bad = dict(profile_from_raw(APP_1001), product="auto")
    with pytest.raises(ValueError):
        intake_agent(APP_1001, FakeLLM(bad))
