def new_case(raw):
    return {
        "id": raw.get("id") or raw.get("applicant_id"),
        "raw_application": raw,
        "profile": None,
        "enrichment": None,
        "risk_score": None,
        "recommendation": None,
        "status": "in_progress",
        "risk_attempts": 0,
        "last_error": None,
        "selected_agents": [],
        "reasoning": None,
        "next_agent": None,
        "trace": [],
    }


def usable_score(score):
    if not isinstance(score, dict):
        return False
    value = score.get("score")
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100:
        return False
    if score.get("band") not in ("low", "moderate", "high", "severe"):
        return False
    return isinstance(score.get("factors"), list) and bool(score["factors"])
