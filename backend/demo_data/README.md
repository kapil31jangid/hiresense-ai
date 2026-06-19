# HireSense AI Demo Dataset

This folder contains a small schema-compatible dataset for local smoke testing.

Generate a demo submission CSV:

```bash
cd backend
python -m app.challenge.offline_ranker --candidates demo_data/candidates.jsonl --output exports/demo_submission.csv --top-k 5
```

Expected behavior:

- `CAND_9000001` should rank near the top because the profile has production AI ranking, embeddings, retrieval, and strong Redrob signals.
- `CAND_9000005` should rank lower because it is research-heavy with weak production and availability signals.
- The CSV columns should be exactly `candidate_id,rank,score,reasoning`.
