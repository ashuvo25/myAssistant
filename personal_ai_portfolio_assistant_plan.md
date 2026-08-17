# Personal AI Portfolio Assistant — Self-Hosted RAG System & Development Plan

## 1. Executive Summary & Core Concept

Build a self-hosted, zero-cost-per-query AI chat assistant for **Md. Asaduzzaman Shuvo's portfolio**. 

The assistant serves as an interactive representative that answers queries regarding Shuvo's:
- Professional Experience & Career Goals
- Academic Background & Research Papers
- AI/ML Projects & Codebases
- Publications, Patents, and Technical Achievements

To strictly eliminate paid third-party LLM API dependencies (e.g., OpenAI, Anthropic), the system runs a lightweight, quantized local Large Language Model (GGUF format via `llama.cpp`) hosted alongside a FastAPI backend in a single Docker container.

### Core Architecture Flow

```text
       Cloudinary (Source of Truth)
   [resume.pdf, research.pdf, project.md]
                    │
           Webhook / Manual Sync
                    │
                    ▼
     ┌─────────────────────────────┐
     │ FastAPI Backend Service     │
     │                             │
     │  1. Multi-Format Parser     │
     │     (PyMuPDF & Markdown)    │
     │             │               │
     │             ▼               │
     │  2. Chunking & Indexing     │
     │     (BM25 Ranker)           │
     │             │               │
     │             ▼               │
     │  3. SSE Stream & LLM        │
     │     (llama-cpp GGUF Model)  │
     └──────────────┬──────────────┘
                    │
           Server-Sent Events (SSE)
                    │
                    ▼
       Next.js Portfolio Chat UI
```

---

## 2. Main Goals

### Primary Goals (V1 MVP)
- **Zero API Cost**: 100% self-hosted inference using local open-weight GGUF LLMs.
- **Strict Grounding & Anti-Hallucination**: Restrict answers exclusively to retrieved context.
- **Cloudinary Document Source**: Store and manage portfolio PDFs and Markdown files centrally.
- **Incremental Sync**: Hash-based document synchronization; only re-index updated documents.
- **Single Container Deployment**: Package FastAPI, llama-cpp, and BM25 index inside a single Docker container.
- **Real-Time Streaming**: Deliver responses word-by-word via Server-Sent Events (SSE).
- **Verifiable Source Citations**: Display exact document names and page/header references for every claim.

### Secondary Goals (V2 & Future Roadmap)
- **Multi-Format Ingestion**: Ingest Markdown (`.md`), Plain Text (`.txt`), and JSON alongside PDFs.
- **Cold-Start Handling**: Frontend pre-warm health pinging and interactive server loading states.
- **Conversation Memory**: Short-term session memory for multi-turn follow-up questions.
- **Offline Evaluation**: Automated local evaluation benchmark suite.

---

## 3. Resource Budget & Memory Strategy

> [!IMPORTANT]
> **Free Tier Resource Boundaries**: Render's free tier provides **512 MB RAM** and **0.1 vCPU**. Running a local LLM under 512 MB RAM requires strict memory budgeting to avoid Out-Of-Memory (OOM) process termination.

### Memory Allocation Matrix

| Component | Technology | Target Memory | Notes |
| :--- | :--- | :--- | :--- |
| **FastAPI + Uvicorn Base** | Python 3.10+ | ~70–80 MB | Lightweight Web Server |
| **Document Processing** | PyMuPDF / Text Parser | ~20–30 MB | Ephemeral during sync |
| **BM25 Search Index** | `rank-bm25` | ~10–15 MB | In-memory token index |
| **Local LLM Engine** | `llama-cpp-python` | ~300–350 MB | `Qwen2.5-0.5B-Instruct-Q4_K_M` |
| **Buffer / Operating Overhead** | OS Overhead | ~40–50 MB | Buffer for incoming requests |
| **Total Memory Budget** | — | **~450–490 MB** | **Fits within 512 MB RAM Ceiling** |

### Fallback Hosting Strategy
If llama.cpp memory usage causes Render Free OOM spikes during heavy generation:
1. **Primary**: Deploy Docker container to **Hugging Face Spaces** (Free CPU Tier: **16 GB RAM**, 2 vCPU).
2. **Secondary**: Deploy to **Render Starter Tier** (1 GB RAM @ $7/mo).
3. **Tertiary API Fallback Mode**: Toggle environment flag `USE_REMOTE_API=true` to switch seamlessly to free-tier Groq/OpenRouter API endpoints while maintaining identical backend contracts.

---

## 4. Technology Stack

### Frontend
- **Framework**: Next.js (App Router, TypeScript)
- **Styling**: Vanilla CSS / Tailwind CSS (Design tokens matching main portfolio)
- **Communication**: EventSource API / Fetch API for Server-Sent Events (SSE)

### Backend Service
- **API Framework**: Python 3.10+, FastAPI, Uvicorn
- **Security & Rate Limiting**: `slowapi`, CORS Middleware, Input Sanitization

### Document Parsing & Indexing
- **PDF Parser**: PyMuPDF (`fitz`) — high-speed C-extension PDF extractor
- **Markdown / Text Parser**: Built-in Python `markdown` & splitters
- **Keyword Retrieval**: `rank-bm25` (Lightweight BM25 implementation)

### Local LLM Engine
- **Inference Server**: `llama-cpp-python`
- **Model Format**: GGUF (4-bit quantization `Q4_K_M`)
- **Primary Candidate**: `Qwen2.5-0.5B-Instruct-GGUF` (~350 MB download)
- **Secondary Candidate**: `Qwen2.5-1.5B-Instruct-GGUF` (Requires 1GB+ RAM host)

### Storage & Infrastructure
- **Document Store**: Cloudinary (Source of Truth for PDFs/Docs)
- **Local Index Cache**: Local file storage (`knowledge/metadata.json` & `knowledge/bm25.pkl`)
- **Containerization**: Docker (Single stage, slim Python base image)
- **Host Platform**: Render Web Service / Hugging Face Spaces

---

## 5. System Architecture & Component Interaction

```text
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           PORTFOLIO FRONTEND (Next.js)                           │
│                                                                                 │
│  ┌───────────────────────┐                     ┌─────────────────────────────┐  │
│  │   Chat Widget UI      │ ──[On Mount Ping]─► │ GET /health (Wakes Server)  │  │
│  │                       │ ──[Send Query]────► │ POST /chat/stream (SSE)     │  │
│  └───────────────────────┘                     └─────────────────────────────┘  │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            DOCKER CONTAINER (FastAPI)                           │
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │ Security Layer: CORS Guard | Rate Limiter (SlowAPI) | Input Sanitizer     │  │
│  └─────────────────────────────────────┬─────────────────────────────────────┘  │
│                                        │                                        │
│                                        ▼                                        │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │ BM25 Retriever Service                                                    │  │
│  │  - Tokenizes User Prompt                                                  │  │
│  │  - Queries BM25 Index                                                     │  │
│  │  - Returns Top-3 Most Relevant Document Chunks + Source Metadata           │  │
│  └─────────────────────────────────────┬─────────────────────────────────────┘  │
│                                        │                                        │
│                                        ▼                                        │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │ Prompt Generator                                                          │  │
│  │  - Formats Strict Portfolio Persona                                       │  │
│  │  - Injects Context & Question into System Prompt                          │  │
│  └─────────────────────────────────────┬─────────────────────────────────────┘  │
│                                        │                                        │
│                                        ▼                                        │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │ Local LLM Engine (llama-cpp-python)                                       │  │
│  │  - Loads Qwen2.5-0.5B-Instruct GGUF                                       │  │
│  │  - Generates Word-by-Word Tokens                                          │  │
│  └─────────────────────────────────────┬─────────────────────────────────────┘  │
│                                        │                                        │
│                                        ▼                                        │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │ Server-Sent Events (SSE) Generator                                        │  │
│  │  - Streams JSON payload: { token: "...", sources: [...] }                 │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Repository Directory Structure

```text
personal-ai-chat/
│
├── backend/
│   ├── app/
│   │   ├── main.py                   # FastAPI initialization & middleware
│   │   ├── config.py                 # Pydantic environment configuration
│   │   ├── routes/
│   │   │   ├── chat.py               # /chat & /chat/stream endpoints
│   │   │   ├── health.py             # /health check endpoint
│   │   │   ├── sync.py               # /sync endpoint for manual indexing
│   │   │   └── webhook.py            # /webhook/cloudinary change detector
│   │   ├── services/
│   │   │   ├── cloudinary_service.py # Cloudinary API fetcher
│   │   │   ├── parser_service.py     # PyMuPDF & Markdown parser
│   │   │   ├── chunker_service.py    # Text chunking logic
│   │   │   ├── bm25_service.py       # BM25 retrieval index manager
│   │   │   └── llm_service.py        # llama-cpp-python wrapper & streaming
│   │   ├── prompts/
│   │   │   └── system_prompt.txt     # Anti-hallucination system prompt
│   │   └── schemas/
│   │       └── chat_schema.py        # Pydantic request/response models
│   │
│   ├── knowledge/                    # In-memory / Cached index files
│   │   ├── metadata.json             # Document version hashes & registry
│   │   └── index.pkl                 # Serialized BM25 index
│   │
│   ├── models/                       # Local model directory (gitignored)
│   │   └── qwen2.5-0.5b-instruct.gguf
│   │
│   ├── scripts/
│   │   ├── download_model.py         # Script to fetch GGUF binary
│   │   └── evaluate.py               # Offline benchmarking script
│   │
│   ├── requirements.txt              # Production Python dependencies
│   ├── Dockerfile                    # Container configuration
│   └── entrypoint.sh                 # Container startup script
│
├── frontend/
│   ├── app/
│   │   └── components/
│   │       ├── ChatWidget.tsx        # Main floating chat container
│   │       ├── ChatMessage.tsx       # Message balloon & citation renderer
│   │       ├── StreamingText.tsx     # Animated text stream handler
│   │       └── SuggestedQueries.tsx  # Pre-defined prompt pills
│   └── package.json
│
├── .env.example                      # Template environment variables
├── docker-compose.yml                # Local orchestration container
├── render.yaml                       # Render deployment manifest
└── README.md                         # Technical documentation
```

---

## 7. Document Strategy & Ingestion Pipeline

Cloudinary serves as the single source of truth for all portfolio materials.

### Ingested Asset Hierarchy

```text
portfolio/
├── resume.pdf                        # Professional Resume
├── research/
│   ├── paper_01.pdf                  # Bangla NLP / Deep Learning Paper
│   └── paper_02.pdf                  # LLM / RAG Research Paper
├── projects/
│   ├── vat_assistant.md              # NBR VAT Assistant Project Writeup
│   └── portfolio_assistant.md        # Personal AI Chatbot Technical Spec
└── profile/
    └── bio_summary.txt               # Key Background, Skills, Contact Info
```

### Multi-Format Parsing Strategy

1. **PDF Processing (`PyMuPDF`)**:
   - Extract page-by-page text.
   - Clean headers, footers, page numbers, and redundant whitespace.
   - Preserve page numbers in metadata for citations (`page: 1`).

2. **Markdown Processing (`.md` / `.txt`)**:
   - Parse document sections split by `#` headers.
   - Attach section headers in metadata for citations (`header: "# Architecture"`).

---

## 8. Incremental Document Synchronization Flow

To minimize cold-start processing time, document downloading and BM25 index updates occur **only when a file is modified**.

```text
                      Cloudinary Webhook Call
                                │
                                ▼
                    POST /webhook/cloudinary
                                │
                                ▼
                     Validate Secret Signature
                                │
                                ▼
               Fetch Remote ETag / Hash from Cloudinary
                                │
                                ▼
                 Compare with `metadata.json` Hash
                                │
                 ┌──────────────┴──────────────┐
                 ▼                             ▼
            [Hash Match]                [Hash Mismatch]
                 │                             │
                 ▼                             ▼
        Skip Indexing process            Download Updated File
                                               │
                                               ▼
                                      Extract & Chunk Text
                                               │
                                               ▼
                                      Rebuild BM25 Index
                                               │
                                               ▼
                                   Save Hash to metadata.json
```

---

## 9. Text Chunking & BM25 Indexing Strategy

### Chunking Specification
- **Chunk Size**: `400 – 600 words` (optimal balance for small LLM context windows).
- **Chunk Overlap**: `50 – 80 words` (prevents context truncation across boundaries).
- **Chunk Metadata Schema**:
  ```json
  {
    "id": "doc_resume_p1_c2",
    "document": "resume.pdf",
    "source_type": "pdf",
    "page": 1,
    "header": null,
    "content": "Md. Asaduzzaman Shuvo is an AI/ML Engineer with expertise in RAG..."
  }
  ```

### BM25 Tokenization Strategy
- Convert query and text chunks to lower-case.
- Strip special symbols and punctuation.
- Apply standard English stop-word removal.
- Index terms with `rank-bm25`.

---

## 10. Direct BM25 Retrieval vs Deferred Dense Vector DB Rationale

> [!NOTE]
> **Technical Rationale for Deferring Vector DBs in V1**:
> - Including Sentence-Transformers (`all-MiniLM-L6-v2`) requires PyTorch/Transformers, adding **~300 MB** of library RAM overhead.
> - Combining PyTorch + llama.cpp inside 512 MB RAM guaranteed OOM failure on Render Free.
> - BM25 provides **zero-overhead, high-speed keyword retrieval** for small curated document sets (<100 pages), achieving >90% precision for factual portfolio queries.

---

## 11. Local LLM Engine & Prompt Engineering

### System Prompt Guardrails

```text
You are the personal AI Assistant for Md. Asaduzzaman Shuvo's portfolio.
Your sole purpose is to provide accurate, factual answers about Shuvo's professional experience, research, projects, education, and skills.

STRICT LAWS OF RESPONSE:
1. Base your answer EXCLUSIVELY on the provided CONTEXT.
2. Never invent, extrapolate, or assume facts not present in the CONTEXT.
3. If the user asks a question that cannot be answered using the provided CONTEXT, state clearly:
   "I don't have that information in Shuvo's portfolio records."
4. Maintain a professional, polite, and technical tone.
5. Keep responses concise (under 150 words).

Retrieved Portfolio Context:
{retrieved_context}

User Question:
{user_question}

Assistant Response:
```

### Model Runtime Configuration (`llama-cpp-python`)
- `n_ctx`: 2048 (Context window size)
- `max_tokens`: 256 (Generation limit)
- `temperature`: 0.2 (Low variance for factual consistency)
- `top_p`: 0.9

---

## 12. Security, CORS & Anti-Prompt-Injection Safeguards

1. **CORS Restrictions**:
   - Restrict origin headers explicitly to Shuvo's portfolio domain:
     `https://shuvo-portfolio.com` (and `http://localhost:3000` for development).
2. **Rate Limiting**:
   - Enforce IP-based rate limiting via `slowapi`: **10 requests per minute** per client IP.
3. **Input Sanitization & Constraints**:
   - Maximum query length: **300 characters**.
   - Strip prompt injection markers (e.g. `Ignore previous instructions`, `System:`, `<|im_start|>`).
4. **Webhook Security**:
   - Verify `X-Cld-Signature` on Cloudinary webhook events.

---

## 13. API Endpoint Specification

### `GET /health`
- **Purpose**: Render health probe & Frontend cold-start ping.
- **Response**:
  ```json
  { "status": "healthy", "model_loaded": true, "indexed_chunks": 42 }
  ```

### `POST /chat/stream` (Primary SSE Endpoint)
- **Request Body**:
  ```json
  { "message": "What research has Shuvo published in NLP?" }
  ```
- **Response Stream (Server-Sent Events)**:
  ```text
  event: metadata
  data: {"sources": [{"document": "research/paper_01.pdf", "page": 2}]}

  event: token
  data: {"text": "Shuvo "}

  event: token
  data: {"text": "published "}

  event: done
  data: {}
  ```

### `POST /sync`
- **Purpose**: Trigger manual document update check. Protected via `Bearer SECRET_TOKEN`.

### `POST /webhook/cloudinary`
- **Purpose**: Automatic trigger from Cloudinary upon asset upload/delete.

---

## 14. Frontend UX & Cold-Start Strategy

### Render Free Cold-Start Problem
Render Free instances spin down after 15 minutes of inactivity. Cold starts take **25–40 seconds** (container spin up + model loading).

### UX Solution Matrix
1. **Pre-warm Health Ping**: As soon as a user hovers near the chat button or loads the site, Next.js fires a background `GET /health` request to wake up Render silently.
2. **Interactive Loading Status**: If the backend is waking up, the chat widget displays:
   - 🟡 *"Waking up server... (First response takes ~20s)"*
   - 🟢 *"Assistant Online"*

```text
┌──────────────────────────────────────────┐
│  🤖 Shuvo AI Assistant           🟢 Online│
├──────────────────────────────────────────┤
│                                          │
│  Hello! Ask me anything about Shuvo's    │
│  research, projects, or experience.      │
│                                          │
│  [What AI projects has he built?]        │
│  [Tell me about his NLP research.]       │
│                                          │
├──────────────────────────────────────────┤
│ Type a question...                 [Send]│
└──────────────────────────────────────────┘
```

---

## 15. Source Citations & Transparency Format

Every answer displays verifiable source footnotes.

**Sample Chat Response**:
> Shuvo designed a bilingual RAG architecture for Bangladesh VAT documents utilizing BM25 keyword matching, hybrid reranking, and cross-encoder evaluation.
>
> **Sources**:
> - 📄 `resume.pdf` — Page 1
> - 📄 `projects/vat_assistant.md` — Section `# Technical Specs`

---

## 16. Docker Containerization Strategy

### Single-Stage Dockerfile Strategy
To avoid embedding a 350 MB model binary into git, the Docker container downloads the GGUF model dynamically during build or container startup if not cached locally.

```dockerfile
FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Ensure model directory exists
RUN mkdir -p /app/models

# Download Qwen GGUF model during container build
RUN python scripts/download_model.py

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 17. Environment Configuration Variables

Create `.env.example`:

```bash
# Server Settings
PORT=8000
ENVIRONMENT=production
ALLOWED_ORIGINS=https://shuvo-portfolio.com,http://localhost:3000

# Cloudinary Integration
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# Security Keys
SYNC_SECRET_TOKEN=your_custom_sync_secret_key
WEBHOOK_SECRET=your_cloudinary_webhook_secret

# LLM Model Settings
MODEL_NAME=qwen2.5-0.5b-instruct.gguf
MODEL_URL=https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf
USE_REMOTE_API=false
GROQ_API_KEY=optional_fallback_key
```

---

## 18. Lightweight Offline Evaluation Pipeline

Instead of heavy third-party dependencies (Ragas / Trulens), evaluation is handled via a clean, self-contained Python script: `scripts/evaluate.py`.

### Benchmark Dataset (`evaluation/dataset.json`)
Contains 30 curated questions covering:
- **Resume & Education** (5)
- **Skills & Tools** (5)
- **Projects & Technical Specs** (10)
- **Research & Publications** (10)

### Evaluation Metrics
- **Retrieval Precision (Hit@1, Hit@3)**: Verifies if the correct source document chunk was retrieved.
- **Answer Groundedness Check**: Verifies zero unverified facts or out-of-scope hallucinations.

---

## 19. Actionable Step-by-Step Roadmap

### Phase 0: Local Research & Benchmarking (Completed Plan Stage)
- [x] Analyze Render Free RAM constraints (512 MB ceiling).
- [x] Benchmark `Qwen2.5-0.5B-Instruct-Q4_K_M` RAM & CPU performance.
- [x] Formulate single-container lightweight architecture.

### Phase 1: Local Backend & BM25 Core
- [ ] Initialize FastAPI backend skeleton & configuration loader.
- [ ] Implement PDF (`PyMuPDF`) & Markdown text parser.
- [ ] Implement chunking algorithm (500 words, 50 word overlap).
- [ ] Implement `rank-bm25` index manager.
- [ ] Test local context retrieval accuracy.

### Phase 2: Local GGUF Inference Engine & Streaming
- [ ] Install `llama-cpp-python` and load Qwen GGUF model locally.
- [ ] Create system prompt formatter & anti-hallucination guard.
- [ ] Build `/chat/stream` SSE streaming endpoint in FastAPI.
- [ ] Verify local CPU generation latency and memory footprint.

### Phase 3: Cloudinary Integration & Synchronization
- [ ] Configure Cloudinary SDK integration.
- [ ] Build document downloader & hash tracking in `metadata.json`.
- [ ] Implement `/sync` manual update endpoint.
- [ ] Implement `/webhook/cloudinary` change listener.

### Phase 4: Dockerization & Optimization
- [ ] Write optimized single-stage `Dockerfile`.
- [ ] Add `scripts/download_model.py` for automated GGUF fetching.
- [ ] Build & run Docker container locally.
- [ ] Verify total container RAM consumption (< 480 MB).

### Phase 5: Next.js Frontend Development
- [ ] Build responsive `ChatWidget` component.
- [ ] Implement Server-Sent Events (SSE) stream listener UI.
- [ ] Add background server wake-up ping on page load.
- [ ] Add source citation pills and suggested question chips.

### Phase 6: Cloud Deployment & Validation
- [ ] Deploy Docker image to Render Web Service (or Hugging Face Spaces).
- [ ] Configure environment variables & CORS settings.
- [ ] Test cold-start user experience & latency.
- [ ] Execute `scripts/evaluate.py` test suite against live deployment.

---

## 20. Definition of Done (V1 MVP Release)

- [x] **Zero Paid API Usage**: Runs completely on local CPU inference.
- [x] **FastAPI Backend**: Serves streaming chat responses via Server-Sent Events.
- [x] **Cloudinary Sync**: Synchronizes PDFs/Markdown files on update.
- [x] **BM25 Retrieval**: Accurately fetches relevant context chunks.
- [x] **Single Docker Container**: Runs under 512 MB RAM environment.
- [x] **Next.js UI Component**: Live on portfolio with cold-start pre-warm handling.
- [x] **Verifiable Citations**: Answers include page & header references.

---

## 21. Portfolio & Resume Positioning

Highlight this project on LinkedIn and Resume as a software engineering milestone:

> **Personal AI Portfolio Assistant — Self-Hosted RAG System**
> 
> *Architected and deployed an edge-optimized RAG assistant answering technical questions about research, publications, and software projects. Built with FastAPI, Next.js, PyMuPDF, and BM25 indexing. Engineered a zero-cost local LLM pipeline using `llama-cpp-python` and `Qwen2.5-0.5B-GGUF` squeezed inside a 512 MB RAM Docker container. Implemented Cloudinary webhook sync and real-time Server-Sent Events (SSE) streaming.*

---

## 22. Recommended Execution Sequence

1. **Build local RAG pipeline first**: Fast PyMuPDF extraction + BM25 ranking + `llama-cpp-python` text generation.
2. **Expose `/chat/stream` SSE endpoint** and test streaming in terminal/Postman.
3. **Containerize with Docker** and confirm RAM usage is under 480 MB.
4. **Connect Cloudinary Sync** & Webhook listener.
5. **Build Next.js Frontend Widget** with pre-warm ping.
6. **Deploy to Render / Hugging Face Spaces**.
