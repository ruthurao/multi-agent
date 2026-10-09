import json
import os


class LLM:
    def complete(self, agent, system, user):
        self.last_prompt = user
        if os.environ.get("OLLAMA_MODEL"):
            result = _remote("ollama", system, user)
        elif os.environ.get("ANTHROPIC_API_KEY"):
            result = _remote("anthropic", system, user)
        elif os.environ.get("OPENAI_API_KEY"):
            result = _remote("openai", system, user)
        else:
            result = _local(agent, system, user)
        self.last_usage = result["usage"]
        return result


def _tokens(text):
    return len(text) // 4


def _pack(content, system, user, model, provider, usage=None):
    if usage is None:
        incoming = _tokens(system + user)
        outgoing = _tokens(json.dumps(content))
        usage = {"input": incoming, "output": outgoing, "total": incoming + outgoing}
    return {"content": content, "usage": usage, "model": model, "provider": provider}


def _local(agent, system, user):
    if agent == "risk_scoring" and "APP-1004" in user:
        raise TimeoutError("risk scoring timeout")
    payload = json.loads(user)
    if agent == "supervisor":
        from underwriting.agents.supervisor import propose

        content = propose(payload)
    elif agent == "intake":
        from underwriting.agents.intake import profile_from_raw

        content = profile_from_raw(payload)
    elif agent == "enrichment":
        from underwriting.agents.enrichment import lookup_summary

        content = {
            "claims": payload["claims"],
            "credit": payload["credit"],
            "assets": payload["assets"],
            "summary": lookup_summary(payload["claims"], payload["credit"]),
        }
    elif agent == "risk_scoring":
        from underwriting.agents.risk import score_facts

        content = score_facts(payload["enrichment"])
    elif agent == "recommendation":
        from underwriting.agents.recommendation import recommendation_for

        content = recommendation_for(
            {
                "score": payload["score"],
                "band": payload.get("band"),
                "hard_refer": payload.get("hard_refer") or [],
                "factors": ["base"],
            },
            payload.get("fact_summary") or "",
        )
    else:
        content = {"reasoning": agent}
    return _pack(content, system, user, "local", "local")


def _remote(provider, system, user):
    from langchain_core.messages import HumanMessage, SystemMessage

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        model_name = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")
        model = ChatAnthropic(model=model_name)
    elif provider == "ollama":
        from langchain_openai import ChatOpenAI

        model_name = os.environ["OLLAMA_MODEL"]
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        model = ChatOpenAI(model=model_name, base_url=base_url, api_key="ollama")
    else:
        from langchain_openai import ChatOpenAI

        model_name = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        model = ChatOpenAI(model=model_name)
    response = model.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    text = response.content
    if isinstance(text, list):
        text = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in text)
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        content = json.loads(text)
    except json.JSONDecodeError:
        content = {"reasoning": text}
    meta = getattr(response, "usage_metadata", None) or {}
    incoming = meta.get("input_tokens", 0)
    outgoing = meta.get("output_tokens", 0)
    usage = {"input": incoming, "output": outgoing, "total": meta.get("total_tokens", incoming + outgoing)}
    return _pack(content, system, user, model_name, provider, usage)
