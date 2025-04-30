# cpmai

# cpmai

> **Construction Project Management AI**  
> End-to-end micro-services platform that converts raw construction bid packages into structured scopes, risk scores, and professional decision-grade PDF reports.

---

## What is CPM-AI?

CPM-AI is a modular, AWS-native SaaS platform that automates the most tedious parts of GC estimating:

1. **Ingestion & OCR** — Automatically picks up new subcontractor quotes, drawings, specs.  
2. **Parse & Structure** — Converts PDFs into clean JSON (vendor, trade, line-items).  
3. **Vision Classification** — Classifies and embeds permit drawings by trade.  
4. **RAG Scope Extraction** — Reads drawing snippets to generate per-trade scope JSON.  
5. **Risk Scoring** — Predicts missing-scope risk with an XGBoost ensemble.  
6. **Interactive Q&A** — “What’s missing?”, “Who’s best for HVAC?”, via a streaming FastAPI endpoint.  
7. **Final Decision Report** — Auto-generates a polished PDF report in executive or instructional tone.

---

## 🏗️ Architecture Overview

```text
┌──────────────┐      ┌───────────┐      ┌────────────┐
│ File Upload  │────►│ Ingestion │────►│ Object     │
│  (React UI)  │     │ Service   │     │ Storage    │
└──────────────┘     └───────────┘     │ (S3/MinIO) │
        │                    │          └────────────┘
        ▼                    │                │
┌────────────────┐           ▼                │
│  Pre-Processor │──OCR/Text & Vision───────┘
└────────────────┘           │
        │                    ▼
        ▼           ┌──────────────────┐
┌────────────────┐   │ Vector Store     │
│  Quote Parser │──►│ (pgvector)       │
└────────────────┘   └──────────────────┘
        │                    │
        ▼                    ▼
┌──────────────────┐   ┌───────────────┐
│ Trade Scope      │   │ Risk Scoring  │
│ Extractor (RAG)  │   │ (XGBoost)     │
└──────────────────┘   └───────────────┘
        │                    │
        ▼                    ▼
┌───────────────────────────────────────┐
│ Project Evaluator & Assistant (FastAPI│
│  `/query` streaming Q&A)             │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│ Decision Report Generator (Lambda)   │
│  `/generate-report` → Final PDF      │
└───────────────────────────────────────┘
