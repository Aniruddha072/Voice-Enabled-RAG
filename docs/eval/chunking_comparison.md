# Chunking strategy comparison

recall@5 and MRR per strategy, per language, against the golden eval set (`data\eval\golden_set.jsonl`).

| Strategy | Language | N | Recall@5 | MRR |
|---|---|---|---|---|
| fixed_size | en | 101 | 0.950 | 0.614 |
| fixed_size | hi | 101 | 0.871 | 0.539 |
| passage_as_chunk | en | 101 | 0.950 | 0.614 |
| passage_as_chunk | hi | 101 | 0.871 | 0.537 |
| sentence_window | en | 101 | 0.941 | 0.589 |
| sentence_window | hi | 101 | 0.822 | 0.530 |
