import pytest

from underwriting import lookups
from underwriting.agents.enrichment import enrichment_agent, lookup_summary
from underwriting.llm import LLM


class FakeLLM:
    def __init__(self, content):
        self.content = content

    def complete(self, agent, system, user):
        return {"content": self.content, "usage": {"input": 0, "output": 0, "total": 0}}

PROFILE = {
    "applicant_id": "APP-1001",
    "full_name": "Alice Chen",
    "product": "homeowners",
    "complete": True,
    "missing_fields": [],
}


def test_app_1001_lookups():
    result = enrichment_agent(PROFILE, LLM(), lookups)
    assert "claims" in result
    assert "credit" in result
    assert "assets" in result
    assert result["summary"]
    claims = result["claims"]
    if isinstance(claims, dict):
        assert not claims.get("at_fault")
    else:
        assert claims in ([], {})
    assert result["credit"]["band"] == "excellent"


def test_returns_model_summary():
    found = {
        "claims": lookups.claims("APP-1001"),
        "credit": lookups.credit("APP-1001"),
        "assets": lookups.assets("APP-1001"),
        "summary": "excellent credit and no at-fault claims",
    }
    result = enrichment_agent(PROFILE, FakeLLM(found), lookups)
    assert result["summary"] == found["summary"]
    assert result["claims"] == found["claims"]


def test_changed_claims_raise():
    found = {
        "claims": {"at_fault": 9, "not_at_fault": 0, "total_loss": False, "dui_related": False},
        "credit": lookups.credit("APP-1001"),
        "assets": lookups.assets("APP-1001"),
        "summary": lookup_summary({"at_fault": 9}, {"band": "excellent"}),
    }
    with pytest.raises(ValueError):
        enrichment_agent(PROFILE, FakeLLM(found), lookups)
