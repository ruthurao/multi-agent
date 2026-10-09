import json

from underwriting.state import usable_score


def decision_for(score):
    flags = set(score.get("hard_refer") or [])
    value = score["score"]
    if value >= 75:
        return "deny"
    if value <= 34 and not flags:
        return "approve"
    return "refer"


def recommendation_for(score, fact_summary):
    decision = decision_for(score)
    return {"decision": decision, "rationale": f"{decision} at {score['score']}. {fact_summary}".strip()}


def recommendation_agent(score, fact_summary, llm):
    if not usable_score(score):
        raise ValueError("a usable score is required")
    reply = llm.complete(
        "recommendation",
        "Choose approve, deny, or refer and reply with JSON.",
        json.dumps(
            {
                "score": score["score"],
                "band": score["band"],
                "hard_refer": score.get("hard_refer") or [],
                "fact_summary": fact_summary,
            }
        ),
    )
    content = reply["content"]
    rationale = content.get("rationale") if isinstance(content, dict) else None
    if not isinstance(content, dict) or content.get("decision") != decision_for(score):
        raise ValueError("recommendation does not match the rules")
    if not isinstance(rationale, str) or not rationale.strip():
        raise ValueError("recommendation does not match the rules")
    return {"decision": content["decision"], "rationale": rationale}
