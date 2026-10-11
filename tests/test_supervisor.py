from underwriting.agents.supervisor import apply_guard, next_step


def _case(**overrides):
    case = {
        "status": "in_progress",
        "profile": {"complete": True},
        "enrichment": {"summary": "ok"},
        "risk_score": {"score": 13, "band": "low", "factors": ["base"]},
        "recommendation": None,
        "risk_attempts": 0,
    }
    case.update(overrides)
    return case


def test_terminal_status_ends():
    nxt, updates = next_step(_case(status="decided"))
    assert nxt == "end"
    assert updates == {}


def test_incomplete_profile_is_invalid():
    nxt, updates = next_step(_case(profile={"complete": False}, enrichment=None, risk_score=None))
    assert nxt == "end"
    assert updates["status"] == "invalid"


def test_unknown_agent_goes_to_human_review():
    case = _case()
    assert apply_guard(case, {"next_agent": "billing"}) == "end"
    assert case["status"] == "human_review"


def test_recommendation_without_score_is_illegal():
    case = _case(risk_score=None, enrichment=None, profile=None)
    assert apply_guard(case, {"next_agent": "recommendation"}) == "end"
    assert case["status"] == "human_review"


def test_risk_after_three_failures_is_illegal():
    case = _case(risk_score=None, risk_attempts=3)
    assert apply_guard(case, {"next_agent": "risk_scoring"}) == "end"
    assert case["status"] == "human_review"
    assert case["last_error"] == "risk_scoring_timeout"
