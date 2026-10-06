import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def event(agent, text_in, text_out, started, usage=None):
    usage = usage or {"input": 0, "output": 0, "total": 0}
    return {
        "agent": agent,
        "input": text_in,
        "output": text_out,
        "duration_ms": (time.perf_counter() - started) * 1000,
        "tokens": {
            "input": usage.get("input", 0),
            "output": usage.get("output", 0),
            "total": usage.get("total", 0),
        },
    }


def write_trace(case_id, events, root=ROOT):
    path = Path(root) / "traces" / f"{str(case_id).lower()}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(events, indent=2))
    return path
