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
