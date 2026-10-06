# Cost and latency

Nothing in the pipeline changed. These totals are the sum of the events in `traces/app-1001.json`, `traces/app-1002.json`, and `traces/app-1003.json`. Duration is the sum of `duration_ms`. Input, output, and total tokens are summed the same way.

Price assumption: Claude Sonnet, $2 per million input tokens, $10 per million output tokens. The dollar amount for a case is `(input tokens * 2 + output tokens * 10) / 1_000_000`.

| Case | Decision | Input tokens | Output tokens | Total tokens | Duration (ms) | Cost |
| --- | --- | --- | --- | --- | --- | --- |
| APP-1001 | approve | 832 | 98 | 930 | 0.15204097144305706 | $0.002644 |
| APP-1002 | refer | 833 | 98 | 931 | 0.1384170027449727 | $0.002646 |
| APP-1003 | deny | 880 | 98 | 978 | 0.09116681758314371 | $0.002740 |

## Verdict
