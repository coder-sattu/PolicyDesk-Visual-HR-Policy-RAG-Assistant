# Policy Desk: HR Policy RAG Assistant

A small but complete **Retrieval-Augmented Generation (RAG)** chatbot for HR policies, built so you can learn both the
**development** and the **production** side of AI apps.

- **Backend:** FastAPI
- **Orchestration:** LangGraph (two graphs: ingestion and retrieval)
- **Vector DB:** FAISS (persisted to disk)
- **Embeddings:** `BAAI/bge-small-en-v1.5` through fastembed (local ONNX, no torch, no API cost)
- **LLM:** Groq (`llama-3.3-70b-versatile` for answers, `llama-3.1-8b-instant` for query rewriting)
- **UI:** React + Vite. It shows **every pipeline step live**: chunking, embedding, FAISS storage, search scores and generation.
- **Sample data:** `docs/HR_Policy_Handbook.pdf`, a 5-page handbook for a fictional company

---

## 1. Architecture

```
                         ┌──────────────────────── React UI (Vite) ────────────────────────┐
                         │  Upload PDF  →  live pipeline view   |   Chat  +  retrieval trace │
                         └──────────────┬──────────────────────────────────┬────────────────┘
                                        │ POST /api/ingest (NDJSON stream)  │ POST /api/chat (NDJSON stream)
                         ┌──────────────▼──────────────────────────────────▼────────────────┐
                         │                         FastAPI (app/main.py)                     │
                         │                                                                   │
  INGESTION GRAPH        │  validate → load → clean → chunk → embed → store                  │
  (app/ingestion/)       │                                            │                      │
                         │                                            ▼                      │
                         │                                  FAISS index + docstore.json      │
                         │                                            ▲                      │
  RETRIEVAL GRAPH        │  rewrite → embed_query → search → grade ─┬─► generate (Groq)      │
  (app/retrieval/)       │                                          └─► fallback             │
                         └───────────────────────────────────────────────────────────────────┘
```

Each LangGraph node calls `get_stream_writer()` to emit events like
`{"type":"step","step":"chunk","status":"done","data":{...}}`. The graph is run with
`stream_mode=["custom","values"]`, and FastAPI forwards each event to the browser as one line of NDJSON. That is how
the UI can animate each stage as it happens.

## 2. Folder structure

```
hr-policy-rag/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI routes + streaming
│   │   ├── core/
│   │   │   ├── config.py           # all settings (.env)
│   │   │   ├── embeddings.py       # fastembed (real) / hash (offline tests)
│   │   │   ├── vector_store.py     # FAISS IndexIDMap2(IndexFlatIP) + JSON docstore
│   │   │   ├── llm.py              # Groq client (+ mock for tests)
│   │   │   └── events.py           # step event helper for LangGraph
│   │   ├── ingestion/              # ── DATA INGESTION PIPELINE ──
│   │   │   ├── loaders.py          # PDF/TXT/MD → pages
│   │   │   ├── cleaning.py         # header/footer removal, table rows, line wraps
│   │   │   ├── chunking.py         # RecursiveCharacterTextSplitter + section tracking
│   │   │   └── graph.py            # LangGraph: validate→load→clean→chunk→embed→store
│   │   └── retrieval/              # ── RETRIEVAL / RAG PIPELINE ──
│   │       ├── prompts.py          # system + rewrite prompts, context builder
│   │       └── graph.py            # LangGraph: rewrite→embed→search→grade→generate|fallback
│   ├── data/
│   │   ├── sample_docs/            # sample HR handbook
│   │   ├── uploads/                # uploaded files (runtime)
│   │   └── vector_store/           # index.faiss + docstore.json (runtime)
│   ├── tests/                      # pytest: every stage + both graphs + API
│   ├── requirements.txt
│   └── .env.example
├── frontend/                       # React UI
│   └── src/components/             # Track, IngestDetails, AskView, TraceDetails…
├── docs/HR_Policy_Handbook.pdf     # generated sample policy
├── scripts/
│   ├── generate_hr_policy_pdf.py   # regenerate the sample PDF
│   └── ui_smoke_test.py            # headless browser test of the full flow
├── deploy/                         # nginx + systemd for a Linux VM
├── Dockerfile                      # multi-stage: build UI → Python image
├── docker-compose.yml
└── Makefile
```

## 3. Run it locally (development)

**Prerequisites:** Python 3.10+, Node 18+, and a free Groq API key from https://console.groq.com/keys

```bash
# 1. install
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # then put your GROQ_API_KEY in .env

cd ../frontend
npm install

# 2. run (two terminals)
cd backend  && uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev       # open http://localhost:5173
```

Or use the Makefile: `make setup`, then `make backend` and `make frontend` in two terminals.

> **First start:** fastembed downloads the embedding model (~130 MB) into `backend/data/models/`. This happens once.

**Try it:** click **Use the sample HR handbook**, watch the six stations run, then click **Ask a question** and try:

- How many days of sick leave do I get in a year?
- What is the notice period after confirmation?
- Can I work from home during probation?
- *Follow-up:* "and for managers?" (this shows the **rewrite** node using chat history)
- Something off-topic, like "What's the cafeteria menu?" (this shows the **grade → fallback** route)

API docs: http://localhost:8000/docs

## 4. How the pipelines work

### Ingestion (`app/ingestion/graph.py`)

| Node | What it does | Shown in UI |
|---|---|---|
| `validate` | Checks type and size, SHA-256 fingerprint. Re-uploading the same file **replaces** the old copy, so there are no duplicate vectors | size, fingerprint |
| `load` | `pypdf` in **layout mode**, so table rows stay on one line | page tiles + char counts |
| `clean` | Removes repeated headers/footers and "Page N", converts table rows to `a \| b \| c`, joins wrapped lines | raw vs cleaned, removed lines |
| `chunk` | `RecursiveCharacterTextSplitter` (800 chars, 120 overlap). Each chunk records its **page and section heading** | chunk bar + sample chunks |
| `embed` | bge-small, batches of 16, L2-normalised | progress bar, vector colour strip |
| `store` | `faiss.IndexIDMap2(IndexFlatIP)`. Inner product on normalised vectors = cosine similarity. Saved to disk | dot grid of the index |

### Retrieval (`app/retrieval/graph.py`)

| Node | What it does |
|---|---|
| `rewrite` | If there is chat history, Groq's fast 8B model rewrites "and for managers?" into a standalone question |
| `embed_query` | Same embedding model as the chunks (**must match**) |
| `search` | FAISS top-k (default 4) |
| `grade` | Drops chunks below `SCORE_THRESHOLD`. **Conditional edge:** goes to `generate` if any chunk survives, otherwise `fallback` |
| `generate` | Groq 70B streams tokens. The prompt forces context-only answers with `[n]` citations |
| `fallback` | Says it couldn't find the answer, instead of hallucinating |

## 5. Testing

```bash
cd backend && pytest -v          # 12 tests, run fully offline
```

The tests use `EMBEDDING_PROVIDER=hash` (a deterministic offline embedder) and `LLM_PROVIDER=mock`, so they need no
network and no API key. They cover:

- **each stage on its own:** load, clean (footer removed, table values kept), chunk, embed, FAISS add/search/delete/persist
- **the ingestion graph:** all 6 steps emit events, and re-ingesting replaces instead of duplicating
- **the retrieval graph:** answer + sources, empty-index fallback, history rewrite, and a missing Groq key reported as an error
- **the API end to end:** upload → documents → chunks → chat → validation errors → delete → sample → reset

UI test (headless Chrome via Playwright; the backend must be running):

```bash
pip install playwright && playwright install chromium
python scripts/ui_smoke_test.py http://localhost:8000
```

> Tip: run the offline stack with `EMBEDDING_PROVIDER=hash LLM_PROVIDER=mock SCORE_THRESHOLD=0.15 uvicorn app.main:app`
> to develop the UI without internet. The hash embedder is **not semantic**, so answers are poor. Use it for plumbing only.

## 6. Production deployment

### Option A: Docker (simplest)

```bash
cp backend/.env.example backend/.env    # add GROQ_API_KEY
docker compose up --build -d
# open http://localhost:8000  (FastAPI serves the built UI too)
```

The Dockerfile builds the UI in a Node stage, then copies `dist/` into a slim Python image. It also bakes in the
embedding model, so containers start without downloading anything. The FAISS index and uploads live in named
volumes, so they survive restarts.

### Option B: Linux VM with Nginx + systemd

```bash
# on the server
sudo git clone <your-repo> /opt/hr-policy-rag && cd /opt/hr-policy-rag
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env && nano .env                     # GROQ_API_KEY, ENVIRONMENT=production
cd ../frontend && npm ci && npm run build             # → frontend/dist

sudo chown -R www-data /opt/hr-policy-rag/backend/data
sudo cp deploy/hr-rag.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now hr-rag
sudo cp deploy/nginx.conf /etc/nginx/sites-available/hr-rag
sudo ln -s /etc/nginx/sites-available/hr-rag /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d your-domain.com               # HTTPS
```

Logs: `journalctl -u hr-rag -f`

### Production lessons built into this project

- **`proxy_buffering off` in Nginx.** Without it, Nginx holds back the NDJSON stream and the live steps arrive all at
  once at the end. The API also sends `X-Accel-Buffering: no`.
- **One uvicorn worker.** The FAISS index is held in process memory. With several workers, each would hold its own copy,
  and an upload to one worker would be invisible to the others. To scale out, move to a server-based vector DB
  (Qdrant, pgvector) and run more workers.
- **Same embedding model at ingest and query time.** If you change `EMBEDDING_MODEL`, the vector dimension or meaning
  changes. The store detects a dimension mismatch and starts a fresh index, so re-ingest your documents.
- **Tune `SCORE_THRESHOLD` on real questions.** bge-small cosine scores for relevant chunks are usually 0.55–0.85. Too
  high and good questions hit the fallback; too low and the LLM gets noise. Ask 10–20 real questions and look at the
  score bars in the trace panel.
- **Secrets** live only in `.env`, which is git-ignored.
- **Upload limits:** file type check, 20 MB limit, sanitised filenames, and `client_max_body_size` in Nginx.

### Not included yet (good next steps to learn)

1. **Auth.** Add JWT login (you already know this from Go) and protect `/api/ingest` and delete for HR admins only.
2. **Evaluation.** Write 30 question/answer pairs from the handbook and measure retrieval hit-rate and answer accuracy.
3. **Hybrid search.** Combine BM25 keyword search with FAISS. This helps exact terms like "LWP" or "POSH".
4. **Re-ranking.** Add a cross-encoder re-ranker between `search` and `grade`.
5. **OCR** for scanned PDFs (they currently fail at the `load` step with a clear message).
6. **Observability.** Add LangSmith or OpenTelemetry tracing for each graph node.

## 7. API reference

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Models, settings, index stats |
| POST | `/api/ingest` | multipart `file`; **NDJSON stream** of ingestion events |
| POST | `/api/ingest/sample` | Ingest the bundled sample handbook (stream) |
| GET | `/api/sample` | Download the sample PDF |
| POST | `/api/chat` | `{question, history:[{role,content}]}`; **NDJSON stream** (steps + tokens) |
| GET | `/api/documents` | Indexed documents |
| GET | `/api/documents/{id}/chunks` | All chunks of one document |
| DELETE | `/api/documents/{id}` | Remove a document and its vectors |
| DELETE | `/api/documents` | Clear the whole index |

**Event types in the stream:** `start` (list of steps), `step` (running/done/error + data), `progress` (embedding
batches), `token` (answer text), `complete` (final result), `error`.

Try the stream from the terminal:

```bash
curl -N -X POST localhost:8000/api/chat -H 'content-type: application/json' \
     -d '{"question":"What is the notice period?"}'
```

## 8. Configuration (`backend/.env`)

| Variable | Default | Notes |
|---|---|---|
| `GROQ_API_KEY` | (none) | Required for answers |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Answer model. Check console.groq.com/docs/models if deprecated |
| `GROQ_FAST_MODEL` | `llama-3.1-8b-instant` | Query rewriting |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | 384-dim |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | 800 / 120 | Characters |
| `TOP_K` | 4 | Chunks retrieved |
| `SCORE_THRESHOLD` | 0.45 | Cosine cut-off for the grade node |
| `MAX_UPLOAD_MB` | 20 | |
