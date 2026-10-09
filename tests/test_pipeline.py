import json
from pathlib import Path

from underwriting.fixtures import APP_1001, APP_1002, APP_1003, APP_1005
from underwriting.pipeline import run_case

ROOT = Path(__file__).resolve().parents[1]
FIELDS = {"agent", "input", "output", "duration_ms", "tokens"}


def test_happy_paths():
    expected = [
        (APP_1001, "approve", "app-1001.json"),
        (APP_1002, "refer", "app-1002.json"),
        (APP_1003, "deny", "app-1003.json"),
    ]
    for raw, decision, filename in expected:
        case = run_case(raw)
        assert case["recommendation"]["decision"] == decision
        assert case["selected_agents"] == ["intake", "enrichment", "risk_scoring", "recommendation"]
        events = json.loads((ROOT / "traces" / filename).read_text())
        assert isinstance(events, list) and events
        for item in events:
            assert FIELDS <= item.keys()
            assert set(item["tokens"]) == {"input", "output", "total"}
            if item["agent"] != "retry_backoff":
                assert isinstance(item["input"], dict)
        recommendation = next(item for item in events if item["agent"] == "recommendation")
        assert recommendation["input"]["score"] == case["risk_score"]["score"]
        assert recommendation["output"]["decision"] == decision


def test_missing_product_is_invalid():
    case = run_case(APP_1005)
    assert case["status"] == "invalid"
    assert "enrichment" not in case["selected_agents"]
