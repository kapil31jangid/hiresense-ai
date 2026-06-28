# HireSense AI

HireSense AI is an enterprise-grade candidate ranking platform for the Data & AI hiring challenge. It is designed to understand job descriptions semantically, parse candidate profiles, rank talent with hybrid scoring, and generate recruiter-trustworthy shortlists with grounded explanations.

## What It Does

HireSense AI moves beyond keyword matching and evaluates candidates using structured profile data, semantic retrieval, AI reasoning, and ranking signals. The system is built to work across datasets, with the challenge dataset used as the primary validation target.

## Core Capabilities

- Deep job understanding from natural language job descriptions.
- Candidate profile parsing and structured signal extraction.
- Semantic search with embeddings and vector indexing.
- Hybrid ranking with fit score, confidence score, and missing-skill visibility.
- AI-generated explanations grounded in parsed evidence.
- Analytics dashboards for ranking quality and hiring insights.
- Alerts for low-confidence, stale, failed, or anomalous pipeline states.
- Export of ranked shortlist in submission-ready format.

## Tech Stack

- Frontend: React, Tailwind CSS, Recharts
- Backend: FastAPI, Python
- AI: Sentence Transformers, spaCy, Gemini APIs
- Vector Search: FAISS
- Auth: Firebase Authentication
- Database: Firebase Firestore
- Storage: Google Cloud Storage
- Hosting and compute: Google Cloud Run

## Repository Structure

```text
backend/
  app/
    api/
    common/
    modules/
    exports/
frontend/
```

## Main Modules

- API module: authentication, request validation, routing, tracing, and shared error models.
- Candidate module: resume parsing, profile management, behavioral signal extraction, embedding metadata.
- Job module: job parsing, role intelligence extraction, skill normalization, hiring requirement inference.
- Semantic search module: embedding generation, FAISS indexing, semantic retrieval, vector synchronization.
- Ranking module: weighted hybrid ranking, shortlist generation, fit scoring, confidence scoring, explanations.
- AI module: grounded recruiter explanations, comparative analysis, hallucination prevention, summaries.
- Analytics module: ranking metrics, skill distribution analytics, dashboard metrics, hiring insights.
- Alerts module: low-confidence detection, parsing failures, stale profiles, embedding failures, anomalies.
- Data pipeline module: ingestion jobs, embedding refresh, ranking synchronization, retry-safe processing.
- Frontend module: recruiter dashboard, shortlist views, candidate comparison, analytics, alert indicators.

## API Overview

The backend exposes versioned REST endpoints under `/api/v1`.

- `GET /api/v1/health`
- `POST /api/v1/jobs/parse`
- `POST /api/v1/candidates/parse`
- `POST /api/v1/semantic-search/query`
- `POST /api/v1/rankings/generate`
- `POST /api/v1/ai/compare`
- `GET /api/v1/analytics/summary`
- `GET /api/v1/alerts`
- `POST /api/v1/pipeline/run`

The API returns structured error responses with a `request_id` for traceability.

## Submission Flow

1. Recruiter uploads the job description.
2. Candidate profiles are ingested and parsed.
3. Semantic embeddings are generated and indexed.
4. The ranking engine computes semantic relevance and hybrid scores.
5. The AI layer generates grounded explanations.
6. The frontend shows the ranked shortlist and analytics.
7. The final shortlist is exported as a ranked output file for submission.

## Official Dataset Runner

The organizer dataset is stored in Google Cloud Storage (`hiresense-ai` bucket) and configured to automatically download and index locally on first run.

To set up:
1. Copy `.env.example` to `.env`.
2. Ensure you are authenticated to Google Cloud (run `gcloud auth application-default login` on your local terminal).
3. Prepare the dataset by running:

```bash
cd backend
python -m app.challenge.prepare_dataset
```

This will automatically pull `candidates.jsonl.gz` and `sample_candidates.json` from Google Cloud Storage to your local workspace cache (`backend/data/challenge/`), validate them against the schema, and build the byte-offset index directly over the compressed gzip file.

The sample file does not contain relevance labels. It is used only for schema and feature
inspection, never for fitting or final score calibration. The full `candidates.jsonl.gz` remains
the only inference corpus used by the webapp and final submission.

Generate the final top-100 submission from the default configured dataset:

```bash
cd backend
python -m app.challenge.offline_ranker --top-k 100 --strict
```

Run a faster sample smoke test:

```bash
cd backend
python -m app.challenge.offline_ranker --sample --top-k 10 --output exports/organizer_sample_submission_check.csv
```

The output CSV columns match the organizer contract:

```csv
candidate_id,rank,score,reasoning
```

## Getting Started

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Run Tests

```bash
cd frontend
npm test
```

## Output Files

The project is designed to generate ranked shortlist exports in CSV format from the backend `exports/` directory. These outputs are intended to match the challenge submission format.

## Documentation

- `docs/Planning/markdowns` contains architecture and implementation planning.
- `docs/Modules/markdowns` contains module-level implementation documentation.
- `docs/Rules` contains coding, prompt-engineering, business, and workflow rules for the team.

## Design Principles

- Prioritize semantic understanding over keyword matching.
- Never invent candidate evidence.
- Surface missing required skills explicitly.
- Lower confidence for weak or incomplete profiles.
- Keep API contracts stable and traceable.
- Make explanations recruiter-trustworthy and evidence-based.

## Notes

- The repo is structured to support team-based module ownership.
- Docs and secret files are excluded from version control through `.gitignore`.
- The system is intended to be dataset-agnostic and validated against the hackathon dataset.
- The deployment stack is intended to stay Google Cloud and Firebase first for low-friction setup.
