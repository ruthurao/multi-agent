import time
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from underwriting import lookups
from underwriting.agents.enrichment import enrichment_agent
from underwriting.agents.intake import intake_agent
from underwriting.agents.recommendation import recommendation_agent
from underwriting.agents.risk import risk_scoring_agent
from underwriting.agents.supervisor import supervisor_turn
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


def build_graph(llm):
    def supervisor(state):
        started = time.perf_counter()
        reply = supervisor_turn(state, llm)
        return {
            "next_agent": state["next_agent"],
            "reasoning": state["reasoning"],
            "selected_agents": state["selected_agents"],
            "status": state["status"],
            "last_error": state.get("last_error"),
            "trace": state["trace"] + [event("supervisor", state["id"], f"next={state['next_agent']}", started, reply["usage"])],
        }

    def intake(state):
        started = time.perf_counter()
        profile = intake_agent(state["raw_application"], llm)
        label = "complete" if profile["complete"] else "incomplete"
        return {
            "profile": profile,
            "trace": state["trace"] + [event("intake", state["id"], label, started, llm.last_usage)],
        }

    def enrichment(state):
        started = time.perf_counter()
        found = enrichment_agent(state["profile"], llm, lookups)
        return {
            "enrichment": found,
            "trace": state["trace"] + [event("enrichment", state["id"], found["credit"]["band"], started, llm.last_usage)],
        }

    def risk_scoring(state):
        started = time.perf_counter()
        score = risk_scoring_agent(state["profile"], state["enrichment"], llm)
        return {
            "risk_score": score,
            "trace": state["trace"] + [event("risk_scoring", state["id"], f"{score['score']} {score['band']}", started, llm.last_usage)],
        }

    def recommendation(state):
        started = time.perf_counter()
        summary = (state.get("enrichment") or {}).get("summary") or ""
        result = recommendation_agent(state["risk_score"], summary, llm)
        return {
            "recommendation": result,
            "trace": state["trace"] + [event("recommendation", state["id"], result["decision"], started, llm.last_usage)],
        }

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
