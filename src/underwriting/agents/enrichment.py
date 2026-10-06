import json


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
    summary = reply["content"].get("summary") or (
        f"credit {found['credit']['band']}, at_fault {found['claims']['at_fault']}"
    )
    return {**found, "summary": summary}
