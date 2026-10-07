import time
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from underwriting import lookups
from underwriting.agents.enrichment import enrichment_agent
from underwriting.agents.intake import intake_agent
from underwriting.agents.recommendation import recommendation_agent
from underwriting.agents.risk import risk_scoring_agent
from underwriting.agents.supervisor import supervisor_turn
from underwriting.db import load_checkpoint, save_case, save_checkpoint
from underwriting.tracing import event


class Case(TypedDict, total=False):
    id: str
    raw_application: dict
    profile: Any
    enrichment: Any
    risk_score: Any
    recommendation: Any
    status: str
    risk_attempts: int
    last_error: Any
    selected_agents: list
    reasoning: Any
    next_agent: Any
    trace: list


def _record(state, **updates):
    data = dict(state)
    data.update(updates)
    return data


def _checkpoint(state, step, db_path, **updates):
    record = _record(state, **updates)
    save_checkpoint(record, step, db_path)
    save_case(record, db_path)


def build_graph(llm, clock, db_path):
    def supervisor(state):
        started = time.perf_counter()
        reply = supervisor_turn(state, llm)
        nxt = state["next_agent"]
        attempts = state.get("risk_attempts") or 0
        extra = []
        if nxt == "risk_scoring" and attempts in (1, 2):
            wait = 0.5 if attempts == 1 else 1.0
            clock.sleep(wait)
            saved = load_checkpoint(state["id"], "enrichment", db_path)
            kept = {
                "risk_attempts": state.get("risk_attempts"),
                "last_error": state.get("last_error"),
                "selected_agents": list(state.get("selected_agents") or []),
                "status": state.get("status"),
                "next_agent": state.get("next_agent"),
                "reasoning": state.get("reasoning"),
                "trace": list(state.get("trace") or []),
            }
            for key, value in saved.items():
                state[key] = value
            for key, value in kept.items():
                state[key] = value
            backoff = event("retry_backoff", state["id"], f"wait={wait}", started)
            backoff["duration_ms"] = wait * 1000
            extra.append(backoff)
        traced = list(state.get("trace") or []) + extra
        traced.append(event("supervisor", state["id"], f"next={nxt}", started, reply["usage"]))
        return {
            "raw_application": state.get("raw_application"),
            "profile": state.get("profile"),
            "enrichment": state.get("enrichment"),
            "risk_score": state.get("risk_score"),
            "recommendation": state.get("recommendation"),
            "status": state.get("status"),
            "risk_attempts": state.get("risk_attempts") or 0,
            "last_error": state.get("last_error"),
            "selected_agents": list(state.get("selected_agents") or []),
            "reasoning": state.get("reasoning"),
            "next_agent": nxt,
            "trace": traced,
        }

    def intake(state):
        started = time.perf_counter()
        profile = intake_agent(state["raw_application"], llm)
        label = "complete" if profile["complete"] else "incomplete"
        traced = state["trace"] + [event("intake", state["id"], label, started, llm.last_usage)]
        _checkpoint(state, "intake", db_path, profile=profile, trace=traced)
        return {"profile": profile, "trace": traced}

    def enrichment(state):
        started = time.perf_counter()
        found = enrichment_agent(state["profile"], llm, lookups)
        traced = state["trace"] + [event("enrichment", state["id"], found["credit"]["band"], started, llm.last_usage)]
        _checkpoint(state, "enrichment", db_path, enrichment=found, trace=traced)
        return {"enrichment": found, "trace": traced}

    def risk_scoring(state):
        started = time.perf_counter()
        try:
            score = risk_scoring_agent(state["profile"], state["enrichment"], llm)
        except TimeoutError as exc:
            traced = state["trace"] + [event("risk_scoring", state["id"], "timeout", started)]
            return {
                "risk_score": None,
                "risk_attempts": (state.get("risk_attempts") or 0) + 1,
                "last_error": str(exc),
                "trace": traced,
            }
        traced = state["trace"] + [event("risk_scoring", state["id"], f"{score['score']} {score['band']}", started, llm.last_usage)]
        _checkpoint(state, "risk_scoring", db_path, risk_score=score, trace=traced)
        return {"risk_score": score, "trace": traced}

    def recommendation(state):
        started = time.perf_counter()
        summary = (state.get("enrichment") or {}).get("summary") or ""
        result = recommendation_agent(state["risk_score"], summary, llm)
        traced = state["trace"] + [event("recommendation", state["id"], result["decision"], started, llm.last_usage)]
        _checkpoint(state, "recommendation", db_path, recommendation=result, trace=traced)
        return {"recommendation": result, "trace": traced}

    graph = StateGraph(Case)
    graph.add_node("supervisor", supervisor)
    graph.add_node("intake", intake)
    graph.add_node("enrichment", enrichment)
    graph.add_node("risk_scoring", risk_scoring)
    graph.add_node("recommendation", recommendation)
    graph.set_entry_point("supervisor")
    graph.add_conditional_edges(
        "supervisor",
        lambda state: state["next_agent"],
        {
            "intake": "intake",
            "enrichment": "enrichment",
            "risk_scoring": "risk_scoring",
            "recommendation": "recommendation",
            "end": END,
        },
    )
    for name in ("intake", "enrichment", "risk_scoring", "recommendation"):
        graph.add_edge(name, "supervisor")
    return graph.compile()


def write_graph_page(path="graph.html") -> str:
    edges = list(build_graph(None, None, None).get_graph().edges)
    labels = {
        "__start__": "start",
        "__end__": "end",
        "supervisor": "supervisor",
        "intake": "intake",
        "enrichment": "enrichment",
        "risk_scoring": "risk scoring",
        "recommendation": "recommendation",
    }
    spots = {
        "__start__": (450, 56),
        "supervisor": (450, 168),
        "intake": (110, 340),
        "enrichment": (300, 340),
        "risk_scoring": (510, 340),
        "recommendation": (740, 340),
        "__end__": (450, 470),
    }
    boxes = []
    for node, (x, y) in spots.items():
        boxes.append(
            f'<rect x="{x - 78}" y="{y - 22}" width="156" height="44" rx="8" fill="#ffffff" stroke="#111111"/>'
            f'<text x="{x}" y="{y + 5}" text-anchor="middle" font-size="15">{labels[node]}</text>'
        )
    lines = []
    for edge in edges:
        x1, y1 = spots[edge.source]
        x2, y2 = spots[edge.target]
        if edge.conditional and edge.target != "__end__":
            lines.append(
                f'<path d="M {x1} {y1 + 22} C {x1} {y1 + 70}, {x2} {y2 - 70}, {x2} {y2 - 22}" fill="none" stroke="#111111" stroke-dasharray="5 4" marker-end="url(#arrow)"/>'
            )
        elif edge.conditional:
            lines.append(
                f'<path d="M {x1 + 90} {y1} C {x1 + 160} {y1}, {x2 + 160} {y2}, {x2 + 78} {y2}" fill="none" stroke="#111111" stroke-dasharray="5 4" marker-end="url(#arrow)"/>'
            )
        elif edge.source == "__start__":
            lines.append(
                f'<path d="M {x1} {y1 + 22} L {x2} {y2 - 22}" fill="none" stroke="#111111" marker-end="url(#arrow)"/>'
            )
        else:
            lines.append(
                f'<path d="M {x1} {y1 - 22} C {x1} {y1 - 80}, {x2 - 90} {y2 + 40}, {x2 - 78} {y2}" fill="none" stroke="#555555" marker-end="url(#arrow)"/>'
            )
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Underwriting graph</title>
  <style>
    html, body {{ background: #ffffff; color: #111111; }}
    body {{ font-family: system-ui, sans-serif; margin: 2rem; }}
    h1 {{ font-size: 1.25rem; font-weight: 500; }}
  </style>
</head>
<body>
  <h1>Underwriting graph</h1>
  <p>Dashed arrows are the supervisor choice. Gray arrows return to the supervisor.</p>
  <svg viewBox="0 0 900 530" width="100%" style="max-width:900px;height:auto" role="img" aria-label="Underwriting LangGraph">
    <defs>
      <marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
        <path d="M0,0 L8,4 L0,8 Z" fill="#111111"/>
      </marker>
    </defs>
    {''.join(lines)}
    {''.join(boxes)}
  </svg>
</body>
</html>
"""
    from pathlib import Path

    target = Path(path)
    target.write_text(page)
    return str(target.resolve())


if __name__ == "__main__":
    print(write_graph_page())
