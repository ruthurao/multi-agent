import json

from underwriting.state import usable_score

_KNOWN = {"intake", "enrichment", "risk_scoring", "recommendation", "end"}


def next_step(case):
    if case.get("status") in ("decided", "human_review", "invalid"):
        return "end", {}
    if not usable_score(case.get("risk_score")) and case.get("risk_attempts", 0) >= 3:
        return "end", {"status": "human_review", "last_error": "risk_scoring_timeout"}
    profile = case.get("profile")
    if profile is None:
        return "intake", {}
    if not profile.get("complete"):
        return "end", {"status": "invalid"}
    if case.get("enrichment") is None:
        return "enrichment", {}
    if not usable_score(case.get("risk_score")):
        return "risk_scoring", {}
    if case.get("recommendation") is None:
        return "recommendation", {}
    return "end", {"status": "decided"}


def propose(case_slice):
    nxt, _updates = next_step(case_slice)
    return {"next_agent": nxt, "reasoning": f"next is {nxt}"}


def apply_guard(case, proposal):
    proposed = (proposal or {}).get("next_agent")
    missing_score = not usable_score(case.get("risk_score"))
    illegal = proposed not in _KNOWN
    if proposed == "recommendation" and missing_score:
        illegal = True
    if proposed == "risk_scoring" and case.get("risk_attempts", 0) >= 3 and missing_score:
        illegal = True
    if illegal:
        case["status"] = "human_review"
        if case.get("risk_attempts", 0) >= 3 and missing_score:
            case["last_error"] = "risk_scoring_timeout"
        return "end"
    nxt, updates = next_step(case)
    case.update(updates)
    return nxt


def supervisor_turn(case, llm):
    slice_ = {
        "status": case.get("status"),
        "profile": case.get("profile"),
        "enrichment": case.get("enrichment"),
        "risk_score": case.get("risk_score"),
        "recommendation": case.get("recommendation"),
        "risk_attempts": case.get("risk_attempts"),
        "last_error": case.get("last_error"),
    }
    reply = llm.complete(
        "supervisor",
        "Choose the next agent. Reply with JSON.",
        json.dumps(slice_),
    )
    nxt = apply_guard(case, reply["content"])
    selected = list(case.get("selected_agents") or [])
    if nxt != "end":
        selected.append(nxt)
    case["next_agent"] = nxt
    case["reasoning"] = reply["content"].get("reasoning")
    case["selected_agents"] = selected
    return reply
