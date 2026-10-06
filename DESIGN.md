# Design

## Shared case record

The pipeline keeps one case object. Agents do not pass messages to each other. The supervisor reads every section on that object before it chooses the next agent. Intake, enrichment, risk scoring, and recommendation each write only their own section and return to the supervisor. A checkpoint is a copy of that same record, saved after a successful agent, so a retry can resume from the enrichment copy without running intake or enrichment again.

## Case fields

```python
case = {
    "id": "APP-1001",
    "raw_application": {},       # original form, not sent to later prompts
    "profile": None,             # intake
    "enrichment": None,          # enrichment
    "risk_score": None,          # None until a successful score
    "recommendation": None,      # None until recommendation runs
    "status": "in_progress",     # in_progress | decided | human_review | invalid
    "risk_attempts": 0,
    "last_error": None,
    "selected_agents": [],
    "reasoning": None,
    "next_agent": None,
}
```

A usable score is an int from 0 through 100, a band of low, moderate, high, or severe, and a non-empty factors list. Anything else is not a score.

Profile includes `applicant_id`, `full_name`, `product`, `complete` (bool), and `missing_fields` (list). Enrichment includes `claims`, `credit`, `assets`, and `summary`. Recommendation includes `decision` in approve, deny, or refer, and `rationale`.

While a run is in memory the case also holds `trace`, a list of short events. That list is written to `traces/<id>.json` when the run finishes. It is not sent to the next model prompt.

## Read / write

| Agent | Reads | Writes |
| --- | --- | --- |
| Input guardrail | `full_name` and `product` on the raw application | On failure, `status` = invalid and the run stops |
| Supervisor | status, profile, enrichment, risk score, recommendation, risk attempts, last error | `selected_agents` (append when next is not end), `reasoning`, `next_agent`, and `status` when a rule sets it |
| Intake | `raw_application` | `profile` |
| Enrichment | profile, then claims, credit, and assets lookups | `enrichment` |
| Risk scoring | profile and enrichment | `risk_score` on success. On timeout, score stays `None`, `risk_attempts` increments, `last_error` is set |
| Recommendation | the score and a fact summary | `recommendation` |
| Checkpoint | the case after intake, enrichment, a successful score, or recommendation | a copy in SQLite. A timeout is not checkpointed |

Each prompt sees only that agent's slice, not the whole case and not the trace.

## Supervisor rules

The model proposes `next_agent`. `apply_guard(case, proposal)` may override. Rules run in this order:

1. If status is already decided, human_review, or invalid: `next_agent` = end.
2. If there is no usable score and `risk_attempts` >= 3: `next_agent` = end, status human_review, flag `risk_scoring_timeout`. Do not call recommendation.
3. If there is no profile: `next_agent` = intake.
4. If profile is incomplete: `next_agent` = end, status invalid.
5. If there is no enrichment: `next_agent` = enrichment.
6. If there is no usable score: `next_agent` = risk_scoring. This includes retries.
7. If there is no recommendation: `next_agent` = recommendation.
8. If a recommendation exists: `next_agent` = end, status decided.

Illegal proposals are overridden to human review: an unknown `next_agent`, recommendation when the score is missing, and another risk attempt after 3 failures.

Backoff: before the second risk call (`risk_attempts` == 1) sleep 0.5 seconds. Before the third (`risk_attempts` == 2) sleep 1.0 seconds. Then load the checkpoint whose step is enrichment, keep `risk_attempts` and `last_error`, and run risk scoring again. Do not re-run intake or enrichment. Sleep is injected so a test can record the waits. After the third failure, rule 2 sends the case to human review.

## What is not stored

Intake drops bad or missing fields. They are not copied onto the profile. A failed risk call does not write a partial score: `risk_score` stays None. Recommendation does not run, and no recommendation dict is stored, unless a usable score is already on the case.
