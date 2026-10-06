import pytest

from underwriting import lookups
from underwriting.agents.enrichment import enrichment_agent
from underwriting.agents.risk import risk_scoring_agent
from underwriting.llm import LLM


def _profile(applicant_id, name):
    return {
        "applicant_id": applicant_id,
        "full_name": name,
        "product": "homeowners",
        "complete": True,
        "missing_fields": [],
    }


def test_app_1001_low_score():
    profile = _profile("APP-1001", "Alice Chen")
    enrichment = enrichment_agent(profile, LLM(), lookups)
    score = risk_scoring_agent(profile, enrichment, LLM())
    assert isinstance(score["score"], int)
    assert score["band"] == "low"
    assert score["factors"]


def test_app_1003_severe_score():
    profile = _profile("APP-1003", "Jordan Pike")
    enrichment = enrichment_agent(profile, LLM(), lookups)
    score = risk_scoring_agent(profile, enrichment, LLM())
    assert score["score"] >= 75
    assert score["band"] == "severe"


def test_missing_enrichment_raises():
    with pytest.raises(ValueError):
        risk_scoring_agent(_profile("APP-1001", "Alice Chen"), None, LLM())
