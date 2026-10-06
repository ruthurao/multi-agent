import json

_FIELDS = ("applicant_id", "full_name", "product")


def intake_agent(raw_application, llm):
    kept = {key: raw_application[key] for key in _FIELDS if raw_application.get(key)}
    llm.complete("intake", "Read only the supplied fields and reply with JSON.", json.dumps(kept))
    missing = [key for key in _FIELDS if key not in kept]
    profile = {"complete": not missing, "missing_fields": missing}
    profile.update(kept)
    return profile
