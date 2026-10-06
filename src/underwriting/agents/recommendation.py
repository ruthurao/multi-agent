import json


def _usable(score):
    if not isinstance(score, dict):
        return False
    value = score.get("score")
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100:
        return False
    if score.get("band") not in ("low", "moderate", "high", "severe"):
        return False
    return isinstance(score.get("factors"), list) and bool(score["factors"])


def recommendation_agent(score, fact_summary, llm):
    if not _usable(score):
        raise ValueError("a usable score is required")
    llm.complete(
        "recommendation",
        "Choose approve, deny, or refer and reply with JSON.",
        json.dumps({"score": score["score"], "band": score["band"], "fact_summary": fact_summary}),
    )
    flags = set(score.get("hard_refer") or [])
    value = score["score"]
    if value >= 75:
        decision = "deny"
    elif value <= 34 and not flags:
        decision = "approve"
    else:
        decision = "refer"
    return {"decision": decision, "rationale": f"{decision} at {value}. {fact_summary}".strip()}
