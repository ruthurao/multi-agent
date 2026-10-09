# Cost and latency

These totals are the sum of the events in `traces/app-1001.json`, `traces/app-1002.json`, and `traces/app-1003.json`. Duration is the sum of `duration_ms`. Input, output, and total tokens are summed the same way. Each event records the JSON that agent received and the section it wrote, and those objects are included in the output-token counts.

Price assumption: Claude Sonnet, $2 per million input tokens, $10 per million output tokens. The dollar amount for a case is `(input tokens * 2 + output tokens * 10) / 1_000_000`.

| Case | Decision | Input tokens | Output tokens | Total tokens | Duration (ms) | Cost |
| --- | --- | --- | --- | --- | --- | --- |
| APP-1001 | approve | 837 | 211 | 1048 | 0.20008115097880363 | $0.003784 |
| APP-1002 | refer | 838 | 213 | 1051 | 0.15837408136576414 | $0.003806 |
| APP-1003 | deny | 903 | 237 | 1140 | 0.1372491242364049 | $0.004176 |

## Verdict

Overnight batch. A case costs about $0.0038 to $0.0042 at the Claude Sonnet price above, which is cheap enough for a live quote or a nightly run. The durations in the table are local function time, under a millisecond, from the built-in model with no network call. A happy path makes nine model calls in sequence: five supervisor turns and one each for intake, enrichment, risk scoring, and recommendation. A live model round-trip of a few hundred milliseconds makes that several seconds, and a risk timeout adds another 1.5 seconds of backoff before human review. That wait fits an overnight batch. It is too slow for a decision while the applicant is waiting.
