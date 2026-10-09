import pytest

from underwriting.agents.recommendation import recommendation_agent, recommendation_for
from underwriting.llm import LLM


class FakeLLM:
    def __init__(self, content):
        self.content = content

    def complete(self, agent, system, user):
        return {"content": self.content, "usage": {"input": 0, "output": 0, "total": 0}}


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


def test_returns_matching_model_reply():
    score = {"score": 20, "band": "low", "factors": ["base"], "hard_refer": []}
    expected = recommendation_for(score, "no hard-refer flags")
    assert recommendation_agent(score, "no hard-refer flags", FakeLLM(expected)) == expected


def test_wrong_decision_raises():
    score = {"score": 20, "band": "low", "factors": ["base"], "hard_refer": []}
    bad = {"decision": "deny", "rationale": "deny at 20"}
    with pytest.raises(ValueError):
        recommendation_agent(score, "no hard-refer flags", FakeLLM(bad))
