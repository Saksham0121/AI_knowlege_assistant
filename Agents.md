# InsightFlow AI - Enterprise Knowledge Assistant (RAG)

## Project Overview

Build a production-grade Enterprise Knowledge Assistant powered by Retrieval-Augmented Generation (RAG).

The system should allow organizations to upload internal documents such as PDFs, Word documents, PowerPoint presentations, policies, SOPs, compliance manuals, technical documentation, HR guidelines, contracts, and reports.

Users should be able to ask natural language questions and receive accurate answers generated only from the uploaded knowledge base, along with source citations and confidence scores.

The system should be scalable, modular, secure, and enterprise-ready.

---

# Primary Objectives

1. Eliminate manual document searching.
2. Provide instant answers from enterprise knowledge.
3. Prevent AI hallucinations through retrieval-based grounding.
4. Enable department-wise knowledge management.
5. Generate analytics about knowledge usage.
6. Support future enterprise-scale deployment.

---

# Technology Stack

## Frontend

- React.js
- Vite
- Tailwind CSS
- ShadCN UI
- React Query
- Recharts

## Backend

- FastAPI
- LangChain

## Database

- MongoDB

## Vector Database

- ChromaDB (MVP)

Future:
- Pinecone
- Weaviate

## AI Services

- Gemini API
- Sentence Transformers

## Authentication

- JWT Authentication

## Deployment

- Docker
- Nginx
- AWS / Azure / GCP

---

# User Roles

## Employee

Permissions:

- Login
- Ask questions
- View citations
- View chat history
- Give feedback

Restrictions:

- Cannot upload documents
- Cannot manage users

---

## Manager

Permissions:

- Upload documents
- Manage department documents
- View department analytics
- View query reports

---

## Admin

Permissions:

- Full system access
- Manage users
- Manage documents
- View global analytics
- Configure system settings

---

# System Architecture

User

↓

React Frontend

↓

FastAPI Backend

↓

Authentication Layer

↓

Document Processing Service

↓

Embedding Service

↓

Vector Database

↓

Retrieval Engine

↓

LLM Generation Layer

↓

Response + Citations

---

# Module 1 - Authentication System

Implement JWT Authentication.

Features:

- Signup
- Login
- Logout
- Refresh Tokens
- Password Hashing
- Role-Based Access Control

Database Collection:

json {   "_id": "user_id",   "name": "John Doe",   "email": "john@company.com",   "role": "employee",   "department": "HR" } 

---

# Module 2 - Document Upload Service

Supported Formats:

- PDF
- DOCX
- TXT
- PPTX

Maximum File Size:

100 MB

Storage Structure:

text storage/  ├── raw_documents/  ├── processed_documents/  └── metadata/ 

Metadata Example:

json {   "document_id": "DOC001",   "title": "HR Policy",   "department": "HR",   "uploaded_by": "Admin",   "upload_date": "2026-06-10",   "status": "processed" } 

---

# Module 3 - Data Ingestion Pipeline

## Step 1

Receive document.

## Step 2

Extract text.

Libraries:

### PDF

PyMuPDF

### DOCX

python-docx

### PPTX

python-pptx

### TXT

Native Reader

---

## Step 3

Clean text.

Remove:

- Headers
- Footers
- Multiple spaces
- Empty lines
- Invalid characters

Normalize:

- Unicode
- Formatting
- Line breaks

Store cleaned text.

---

# Module 4 - Intelligent Chunking Engine

## Purpose

Large documents exceed LLM context windows.

Split documents into smaller chunks.

---

## Chunking Strategy

Recursive Character Text Splitter

Configuration:

python chunk_size = 700 chunk_overlap = 100 

---

Example:

Chunk 1

Page 1 + Page 2

Chunk 2

Last 100 tokens from Chunk 1
+
New Content

---

Store:

json {   "chunk_id": "CH001",   "document_id": "DOC001",   "page_number": 12,   "text": "chunk content" } 

---

# Module 5 - Embedding Generation

Convert each chunk into a vector representation.

Options:

### Gemini Embeddings

Preferred

### Sentence Transformers

Model:

python all-MiniLM-L6-v2 

Store:

json {   "chunk_id": "CH001",   "vector": [0.12,0.34,0.56] } 

---

# Module 6 - Vector Database

Use ChromaDB.

Store:

- Chunk text
- Embeddings
- Metadata
- Page Numbers
- Department Tags

Example:

json {   "chunk_id": "CH001",   "department": "HR",   "page": 12 } 

---

# Module 7 - Semantic Retrieval Engine

User Query

↓

Query Embedding

↓

Similarity Search

↓

Top K Chunks

↓

Reranking

↓

Context Assembly

↓

LLM

---

Configuration:

python top_k = 5 

Similarity Metric:

python Cosine Similarity 

---

# Module 8 - Hybrid Search

Implement both:

## Semantic Search

Vector Similarity

## Keyword Search

BM25

Final Score:

python final_score = (0.7 * semantic_score) + (0.3 * bm25_score) 

Purpose:

Improve retrieval accuracy.

---

# Module 9 - Query Expansion

Before retrieval:

Expand user queries.

Example:

Input:

Leave Policy

Expanded:

- Leave
- Vacation
- Holiday
- Absence
- Paid Time Off

Improves recall.

---

# Module 10 - Reranking Layer

After retrieval:

Use:

- Cross Encoder
- Gemini Reranking

Purpose:

Reorder retrieved chunks by relevance.

Return best chunks to LLM.

---

# Module 11 - RAG Generation

Prompt Template:

text You are an enterprise knowledge assistant.  Answer only from provided context.  If information is unavailable, say: "I could not find relevant information."  Context: {chunks}  Question: {question} 

---

Response Structure:

json {   "answer": "...",   "confidence": 94,   "citations": [] } 

---

# Module 12 - Citation Engine

Every answer must include sources.

Example:

json {   "document": "HR_Policy.pdf",   "page": 14,   "chunk_id": "CH001" } 

UI Example:

[1] HR_Policy.pdf - Page 14

[2] HR_Policy.pdf - Page 15

Clicking citation should open document viewer.

---

# Module 13 - Chat Interface

Features:

- Real-time chat
- Streaming responses
- Citation cards
- Follow-up questions
- Query suggestions

Store history.

---

# Module 14 - Chat History

Store:

json {   "user_id": "123",   "question": "...",   "answer": "...",   "citations": [],   "timestamp": "..." } 

Features:

- Search chats
- Delete chats
- Export chats

---

# Module 15 - Feedback System

Buttons:

👍 Helpful

👎 Not Helpful

Store:

json {   "query_id": "123",   "feedback": "positive" } 

Purpose:

Future model evaluation.

---

# Module 16 - Analytics Dashboard

Metrics:

## User Analytics

- Active Users
- Queries Per User
- Department Usage

## Knowledge Analytics

- Most Referenced Documents
- Most Asked Questions
- Failed Queries

## Performance Analytics

- Average Retrieval Time
- Average LLM Response Time
- Success Rate

---

Charts:

- Query Trends
- Usage Trends
- Department Activity
- Top Documents

---

# Module 17 - Document Summarization

Upon upload:

Automatically generate:

- Summary
- Keywords
- Topics
- Department Classification

Store metadata.

Example:

json {   "summary": "...",   "keywords": ["leave", "vacation"],   "department": "HR" } 

---

# Module 18 - Department Knowledge Bases

Create separate collections.

Examples:

- HR
- Finance
- Legal
- Engineering

Restrict retrieval based on permissions.

---

# Module 19 - Caching Layer

Use Redis.

Cache:

- Frequently asked questions
- Popular retrieval results
- Query embeddings

Goal:

Reduce latency.

---

# Module 20 - Scalability Design

Microservice Architecture:

text Frontend  ↓  API Gateway  ↓  Auth Service  ↓  Document Service  ↓  Embedding Service  ↓  Retrieval Service  ↓  LLM Service  ↓  Analytics Service 

Benefits:

- Independent scaling
- Easier maintenance
- Better fault isolation

---

# Security Requirements

Implement:

- JWT Authentication
- Role-Based Access
- File Validation
- Rate Limiting
- Input Sanitization
- Audit Logs

---

# Future Enhancements

## Multi-Document Reasoning

Compare information across multiple documents.

---

## Knowledge Graph Integration

Visualize relationships between concepts.

---

## Voice Assistant

Speech-to-text

Text-to-speech

---

## Multilingual Support

Support:

- English
- Hindi
- French
- German

---

## Agentic Workflow Support

Examples:

- Generate reports
- Summarize meetings
- Extract compliance violations
- Create action plans

---

# Success Metrics

Target:

- Retrieval Accuracy > 90%
- Response Time < 3 Seconds
- Citation Accuracy > 95%
- User Satisfaction > 90%

---

# Resume Description

Developed a scalable Enterprise Knowledge Assistant using Retrieval-Augmented Generation (RAG) architecture, enabling semantic search and citation-based question answering over organizational documents. Implemented document ingestion pipelines, recursive chunking, embedding generation, hybrid retrieval, reranking, analytics dashboards, and role-based access control using React, FastAPI, MongoDB, ChromaDB, LangChain, and Gemini API. Designed a modular architecture supporting multi-department knowledge bases, enterprise security, and scalable deployment.