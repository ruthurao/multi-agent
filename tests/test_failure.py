from underwriting.fixtures import APP_1001, APP_1004
from underwriting.pipeline import run_case


class FakeClock:
    def __init__(self):
        self.sleeps = []

    def sleep(self, seconds):
        self.sleeps.append(seconds)


def test_timeout_retries_then_human_review(tmp_path):
    clock = FakeClock()
    case = run_case(APP_1004, clock=clock, db_path=tmp_path / "underwriting.sqlite")
    assert case["status"] == "human_review"
    assert case["recommendation"] is None
    assert case["risk_score"] is None
    assert case["risk_attempts"] == 3
    assert clock.sleeps == [0.5, 1.0]
    assert case["selected_agents"].count("risk_scoring") == 3
    assert "recommendation" not in case["selected_agents"]


def test_approve_still_approves(tmp_path):
    case = run_case(APP_1001, db_path=tmp_path / "underwriting.sqlite")
    assert case["recommendation"]["decision"] == "approve"
