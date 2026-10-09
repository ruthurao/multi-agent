import json

_CREDIT = {"excellent": -12, "good": -4, "fair": 12, "poor": 18}


def _band(score):
    if score <= 34:
        return "low"
    if score <= 59:
        return "moderate"
    if score <= 74:
        return "high"
    return "severe"


def score_facts(enrichment):
    claims = enrichment["claims"]
    assets = enrichment["assets"]
    score = 25
    factors = ["base"]
    at_fault = int(claims.get("at_fault") or 0)
    not_at_fault = int(claims.get("not_at_fault") or 0)
    if at_fault:
        score += 14 * at_fault
        factors.append("at_fault")
    if not_at_fault:
        score += 3 * not_at_fault
        factors.append("not_at_fault")
    if claims.get("total_loss"):
        score += 18
        factors.append("total_loss")
    if claims.get("dui_related"):
        score += 12
        factors.append("dui_related")
    band_name = enrichment["credit"]["band"]
    score += _CREDIT[band_name]
    factors.append("credit " + band_name)
    if assets.get("flood_zone") in ("AE", "VE"):
        score += 10
        factors.append("flood")
    if int(assets.get("roof_year") or 9999) <= 2005:
        score += 6
        factors.append("roof")
    if assets.get("unpermitted_structure"):
        score += 8
        factors.append("unpermitted")
    if assets.get("prior_damage"):
        score += 5
        factors.append("prior_damage")
    score = max(0, min(100, score))
    hard = []
    if claims.get("total_loss"):
        hard.append("total_loss")
    if claims.get("dui_related"):
        hard.append("dui_related")
    if at_fault >= 2:
        hard.append("multiple_at_fault_claims")
    if assets.get("flood_zone") in ("AE", "VE"):
        hard.append("high_flood_zone")
    return {"score": score, "band": _band(score), "factors": factors, "hard_refer": hard}


def risk_scoring_agent(profile, enrichment, llm):
    if not enrichment:
        raise ValueError("enrichment is required")
    reply = llm.complete(
        "risk_scoring",
        "Score this application and reply with JSON.",
        json.dumps({"applicant_id": profile.get("applicant_id"), "enrichment": enrichment}),
    )
    content = reply["content"]
    if content != score_facts(enrichment):
        raise ValueError("risk score does not match the rules")
    return content
