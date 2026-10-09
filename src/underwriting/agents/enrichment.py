import json


def lookup_summary(claims, credit):
    return f"credit {credit['band']}, at_fault {claims['at_fault']}"


def enrichment_agent(profile, llm, lookups):
    applicant_id = profile["applicant_id"]
    found = {
        "claims": lookups.claims(applicant_id),
        "credit": lookups.credit(applicant_id),
        "assets": lookups.assets(applicant_id),
    }
    reply = llm.complete(
        "enrichment",
        "Summarize these lookups and reply with JSON.",
        json.dumps({"applicant_id": applicant_id, **found}),
    )
    content = reply["content"]
    if not isinstance(content, dict):
        raise ValueError("enrichment does not match the lookups")
    for key in ("claims", "credit", "assets"):
        if content.get(key) != found[key]:
            raise ValueError("enrichment does not match the lookups")
    summary = content.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("enrichment summary is missing")
    return {"claims": found["claims"], "credit": found["credit"], "assets": found["assets"], "summary": summary}
