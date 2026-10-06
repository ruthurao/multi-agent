from underwriting.graph import build_graph
from underwriting.llm import LLM
from underwriting.state import new_case
from underwriting.tracing import write_trace


def run_case(raw):
    case = new_case(raw)
    if not raw.get("full_name") or not raw.get("product"):
        case["status"] = "invalid"
        return case
    llm = LLM()
    result = build_graph(llm).invoke(case, config={"recursion_limit": 40})
    write_trace(result["id"], result.get("trace") or [])
    return result
