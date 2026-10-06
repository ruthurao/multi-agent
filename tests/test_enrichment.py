from underwriting import lookups
from underwriting.agents.enrichment import enrichment_agent
from underwriting.llm import LLM

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
