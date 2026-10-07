import time

from underwriting.db import DEFAULT_DB, save_case
from underwriting.graph import build_graph
from underwriting.llm import LLM
from underwriting.state import new_case
from underwriting.tracing import write_trace


def run_case(raw, clock=None, db_path=None):
    clock = clock or time
    db_path = db_path or DEFAULT_DB
    case = new_case(raw)
    if not raw.get("full_name") or not raw.get("product"):
        case["status"] = "invalid"
        return case
    try:
        result = build_graph(LLM(), clock, db_path).invoke(case, config={"recursion_limit": 40})
    except Exception as exc:
        case["status"] = "human_review"
        case["last_error"] = str(exc)
        return case
    write_trace(result["id"], result.get("trace") or [])
    save_case(result, db_path)
    return result
