from underwriting.agents.intake import intake_agent
from underwriting.fixtures import APP_1001, APP_1005
from underwriting.llm import LLM


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
