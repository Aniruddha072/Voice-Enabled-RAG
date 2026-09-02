# Latency benchmark

200 queries run, 199 completed without a pipeline error.
1 raised an error (see `latency_results.jsonl` for details).
47 of the completed queries were refused by a guardrail.

## Per-stage latency (ms), all languages combined

| Stage | Mean | P50 | P90 |
|---|---|---|---|
| stt | 912.7 | 587.4 | 1668.7 |
| input_safety | 207.9 | 195.5 | 310.1 |
| embed | 287.8 | 236.9 | 639.2 |
| retrieve | 26.1 | 24.9 | 31.9 |
| relevance | 0.0 | 0.0 | 0.0 |
| generate | 5803.4 | 5735.2 | 9155.4 |
| groundedness | 623.2 | 0.4 | 2554.1 |
| **total** | 6880.8 | 6856.6 | 11048.9 |

## Per-stage latency (ms), by language

| Stage | EN Mean | EN P90 | HI Mean | HI P90 |
|---|---|---|---|---|
| stt | 796.4 | 1227.2 | 1027.9 | 1844.3 |
| input_safety | 234.6 | 353.8 | 181.5 | 239.8 |
| embed | 306.3 | 648.3 | 269.5 | 638.7 |
| retrieve | 24.1 | 29.8 | 28.1 | 34.1 |
| relevance | 0.0 | 0.0 | 0.0 | 0.0 |
| generate | 5150.8 | 9155.4 | 6520.4 | 9058.1 |
| groundedness | 1026.1 | 4967.9 | 153.2 | 0.8 |
| total | 6862.5 | 12991.1 | 6898.8 | 10505.2 |

Retrieval latency sub-200ms at P90: **yes** (mean 26.1ms, P90 31.9ms).

