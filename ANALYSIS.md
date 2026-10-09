# Cost and latency

Nothing in the pipeline changed. These totals are the sum of the events in `traces/app-1001.json`, `traces/app-1002.json`, and `traces/app-1003.json`. Duration is the sum of `duration_ms`. Input, output, and total tokens are summed the same way.

Price assumption: Claude Sonnet, $2 per million input tokens, $10 per million output tokens. The dollar amount for a case is `(input tokens * 2 + output tokens * 10) / 1_000_000`.

| Case | Decision | Input tokens | Output tokens | Total tokens | Duration (ms) | Cost |
| --- | --- | --- | --- | --- | --- | --- |
| APP-1001 | approve | 837 | 211 | 1048 | 0.16495690215379 | $0.003784 |
| APP-1002 | refer | 838 | 213 | 1051 | 0.14612404629588127 | $0.003806 |
| APP-1003 | deny | 903 | 237 | 1140 | 0.1480431528761983 | $0.004176 |

## Verdict
