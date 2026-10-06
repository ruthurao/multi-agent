import pytest

from underwriting.agents.recommendation import recommendation_agent
from underwriting.llm import LLM


def test_low_score_approves():
    result = recommendation_agent(
        {"score": 20, "band": "low", "factors": ["base"], "hard_refer": []},
        "no hard-refer flags",
        LLM(),
    )
    assert result["decision"] == "approve"


def test_moderate_score_refers():
    result = recommendation_agent(
        {"score": 50, "band": "moderate", "factors": ["base"]},
        "moderate",
        LLM(),
    )
    assert result["decision"] == "refer"


def test_severe_score_denies():
    result = recommendation_agent(
        {"score": 90, "band": "severe", "factors": ["base"]},
        "severe",
        LLM(),
    )
    assert result["decision"] == "deny"


def test_missing_score_raises():
    with pytest.raises(ValueError):
        recommendation_agent(None, "none", LLM())
