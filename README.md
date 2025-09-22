# 🏛️ Legal Document Demystifier

AI app to turn dense legal docs into clear, actionable insights with follow‑up Q&A. Built with FastAPI and Google Gemini.

## What it does
- Upload a PDF or paste text; we extract text (PyPDF2 for PDFs)
- Generate a structured analysis: summary, key points, risks, recommendations, simple explanation
- Ask follow‑up questions grounded in the uploaded content, with confidence level and supporting snippets
- Keep a local chat history per session (no DB required)

## Tech stack
- Backend: FastAPI, Uvicorn, requests
- AI: Google Gemini (via HTTPS REST call)
- Parsing: PyPDF2
- Frontend: Jinja2 templates, vanilla JS, CSS (uniform dark theme)
- Env: python‑dotenv; optional Docker and GCP configs included

## Run locally
Prereqs: Python 3.10+, a Gemini API key

1) Install deps
```powershell
pip install -r requirements.txt
```

2) Set environment variable (Windows PowerShell)
```powershell
$env:GEMINI_API_KEY="your-api-key"
```

3) Start the server
```powershell
python main.py
```

Open http://localhost:8080

## Configuration
- GEMINI_API_KEY (required): Google Generative Language API key
- PORT (optional, default 8080)

## Endpoints
- GET /               → UI (upload, analysis, Q&A)
- POST /analyze-document  → file upload (PDF/TXT); returns JSON analysis + document_id
- POST /analyze-text      → raw text; returns JSON analysis + document_id
- POST /ask-question      → question + document_id or document_text; returns answer, relevant_sections, confidence_level
- GET /chat-history       → session chat history
- POST /save-chat         → persist chat in memory for session
- POST /clear-chat-history → clear session chat
- GET /health             → health probe

## How answers are structured
Responses from Gemini are coerced to strict JSON. If parsing fails, we return a graceful fallback with the raw snippet and guidance to retry.

## Security & privacy
- Documents and chats are stored in memory only (per process)
- No external storage; clear chat endpoint included
- Provide your own API key via environment variable

## Deploy
- Dockerfile, app.yaml, and cloudbuild.yaml are provided for Cloud Run/App Engine. Set GEMINI_API_KEY in the environment when deploying.

## Folder guide
```
main.py                 # FastAPI app and endpoints
templates/              # UI templates (layout, index)
static/css/style.css    # Dark theme styles
static/js/app.js        # Frontend logic (upload, results, Q&A, chat)
requirements.txt        # Dependencies
Dockerfile, app.yaml, cloudbuild.yaml
```

## Notes
- The UI is now a uniform dark, blackish palette
- Chat history shows previous Q&A and can be cleared per session
- PDF extraction uses PyPDF2’s text; image‑only PDFs won’t be OCR’d