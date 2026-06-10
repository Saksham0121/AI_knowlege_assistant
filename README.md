# InsightFlow AI — Enterprise RAG Knowledge Assistant

<div align="center">
  <h1>🧠 InsightFlow AI</h1>
  <p><strong>Production-grade Enterprise Knowledge Assistant powered by RAG</strong></p>
  <p>
    <img src="https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi" />
    <img src="https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react" />
    <img src="https://img.shields.io/badge/Gemini-API-4285F4?style=flat-square&logo=google" />
    <img src="https://img.shields.io/badge/ChromaDB-Vector_DB-orange?style=flat-square" />
    <img src="https://img.shields.io/badge/MongoDB-7.0-47A248?style=flat-square&logo=mongodb" />
  </p>
</div>

---

## Overview

InsightFlow AI enables organizations to upload internal documents (PDFs, DOCX, PPTX, TXT) and ask natural language questions — receiving accurate, citation-backed answers generated only from the uploaded knowledge base.

## Features

- 📄 **Document Ingestion** — PDF, DOCX, PPTX, TXT with auto-chunking & embedding
- 🔍 **Hybrid Retrieval** — Semantic (ChromaDB) + Keyword (BM25) search
- 🤖 **RAG Generation** — Grounded answers via Gemini with citation cards
- 📊 **Analytics Dashboard** — Query trends, department activity, top documents
- 🔐 **RBAC** — Employee / Manager / Admin roles with JWT auth
- 🏢 **Department KBs** — Separate collections per department
- ⚡ **Redis Cache** — Embedding & query result caching
- 🐳 **Docker** — Full containerized deployment

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite, Tailwind CSS, ShadCN UI, Recharts |
| Backend | FastAPI, LangChain, Python 3.11 |
| Database | MongoDB (metadata), ChromaDB (vectors) |
| Cache | Redis |
| AI | Gemini API (generation + embeddings) |
| Auth | JWT (access + refresh tokens) |
| Deploy | Docker, Nginx |

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env with your Gemini API key and MongoDB URL

# 2. Start all services
docker-compose up -d

# 3. Access the app
open http://localhost
```

## Development Setup

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Architecture

```
User → React Frontend → FastAPI → Auth → Document Service
                                       → Embedding (Gemini)
                                       → ChromaDB (Vector Search)
                                       → BM25 (Keyword Search)
                                       → Gemini LLM → Response + Citations
```

## Modules

| # | Module | Description |
|---|--------|-------------|
| 1 | Authentication | JWT auth with RBAC |
| 2 | Document Upload | PDF/DOCX/PPTX/TXT ingestion |
| 3 | Data Ingestion | Extract, clean, normalize |
| 4 | Chunking Engine | Recursive splitter (700/100) |
| 5 | Embeddings | Gemini text-embedding-004 |
| 6 | Vector DB | ChromaDB per-department |
| 7 | Retrieval | Cosine similarity, top-k=5 |
| 8 | Hybrid Search | Semantic 70% + BM25 30% |
| 9 | Query Expansion | Gemini-powered expansion |
| 10 | Reranking | Cross-encoder reranking |
| 11 | RAG Generation | LangChain + Gemini Pro |
| 12 | Citation Engine | Source + page citations |
| 13 | Chat Interface | Streaming SSE chat |
| 14 | Chat History | Search, delete, export |
| 15 | Feedback | 👍/👎 per response |
| 16 | Analytics | Dashboards + charts |
| 17 | Auto-Summary | Keywords, topics on upload |
| 18 | Department KBs | Isolated collections |
| 19 | Caching | Redis query/embedding cache |
| 20 | Scalability | Microservice-ready design |

## License

MIT
