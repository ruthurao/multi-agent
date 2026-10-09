import pytest

from underwriting.agents.risk import risk_scoring_agent, score_facts
from underwriting.llm import LLM


def _profile(applicant_id, name):
    return {
        "applicant_id": applicant_id,
        "full_name": name,
        "product": "homeowners",
        "complete": True,
        "missing_fields": [],
    }


ALICE = {
    "claims": {"at_fault": 0, "not_at_fault": 0, "total_loss": False, "dui_related": False},
    "credit": {"band": "excellent"},
    "assets": {"flood_zone": "X", "roof_year": 2019, "unpermitted_structure": False, "prior_damage": False},
    "summary": "credit excellent, at_fault 0",
}

JORDAN = {
    "claims": {"at_fault": 2, "not_at_fault": 0, "total_loss": True, "dui_related": True},
    "credit": {"band": "poor"},
    "assets": {"flood_zone": "AE", "roof_year": 2012, "unpermitted_structure": False, "prior_damage": False},
    "summary": "credit poor, at_fault 2",
}


class FakeLLM:
    def __init__(self, content):
        self.content = content

    def complete(self, agent, system, user):
        return {"content": self.content, "usage": {"input": 0, "output": 0, "total": 0}}


def test_app_1001_low_score():
    score = risk_scoring_agent(_profile("APP-1001", "Alice Chen"), ALICE, LLM())
    assert score["score"] == 13
    assert score["band"] == "low"
    assert score["factors"]


def test_app_1003_severe_score():
    score = risk_scoring_agent(_profile("APP-1003", "Jordan Pike"), JORDAN, LLM())
    assert score["score"] == 100
    assert score["band"] == "severe"


def test_returns_matching_model_reply():
    expected = score_facts(ALICE)
    assert risk_scoring_agent(_profile("APP-1001", "Alice Chen"), ALICE, FakeLLM(expected)) == expected


def test_wrong_score_raises():
    bad = dict(score_facts(ALICE), score=99)
    with pytest.raises(ValueError):
        risk_scoring_agent(_profile("APP-1001", "Alice Chen"), ALICE, FakeLLM(bad))


def test_missing_enrichment_raises():
    with pytest.raises(ValueError):
        risk_scoring_agent(_profile("APP-1001", "Alice Chen"), None, LLM())
