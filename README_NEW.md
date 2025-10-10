# 🏛️ Legal Document Demystifier

AI app to turn dense legal docs into clear, actionable insights with follow‑up Q&A. Built with FastAPI and Google Gemini.

## What it does
- Upload a PDF or paste text; we extract text (PyPDF2 for PDFs)
- Generate a structured analysis: summary, key points, risks, recommendations, simple explanation
- Ask follow-up questions grounded in the uploaded content, with confidence level and supporting snippets
- Keep a local chat history per session (no DB required)

## Tech stack
- Backend: FastAPI, Uvicorn, requests
- AI: Google Gemini (via HTTPS REST call)
- Parsing: PyPDF2
- Frontend: React/Vite app (TypeScript, custom legal document analysis UI)
- Tooling: npm + Vite build pipeline, python-dotenv; Docker & GCP configs included

## Run locally
Prereqs: Python 3.10+, Node.js 18+, a Gemini API key.

### 1) Get a Gemini API Key
Visit https://aistudio.google.com/app/apikey and create a free API key.

### 2) Set up environment variables
```powershell
# Copy the example file
copy .env.example .env
```
Then edit `.env` and replace `your-gemini-api-key-here` with your actual API key.

**OR** set it directly in PowerShell:
```powershell
$env:GEMINI_API_KEY="your-actual-api-key"
```

### 3) Install Python dependencies
```powershell
pip install -r requirements.txt
```

### 4) Install frontend dependencies & build once (outputs to `client/dist`)
```powershell
npm install --legacy-peer-deps
npm run client:build
```

> Tip: for iterative UI work run `npm run client` in a second terminal (Vite dev server on http://localhost:8441). The FastAPI backend continues to run on http://localhost:8080.

### 5) Start the backend
```powershell
python main.py
```

Open http://localhost:8080. FastAPI now serves the built React SPA.

## Configuration
- **GEMINI_API_KEY** (required): Google Generative Language API key
- **PORT** (optional, default 8080)

## Endpoints
- GET /               → React SPA entry point (Legal Document Demystifier UI)
- GET /assets/*       → Hashed static assets served from Vite build output
- POST /analyze-document  → file upload (PDF/TXT); returns JSON analysis + document_id
- POST /analyze-text      → raw text; returns JSON analysis + document_id
- POST /ask-question      → question + document_id or document_text; returns answer, relevant_sections, confidence_level
- POST /save-chat         → persist chat in memory for session
- GET /chat-history       → session chat history
- POST /clear-chat-history → clear session chat
- GET /health             → health probe

## How answers are structured
Responses from Gemini are coerced to strict JSON. If parsing fails, we return a graceful fallback with the raw snippet and guidance to retry.

## Security & privacy
- Documents and chats are stored in memory only (per process)
- No external storage; clear chat endpoint included
- Provide your own API key via environment variable

## Deploy
- Dockerfile now performs a multi-stage build (Node → Python) so the React assets are bundled automatically.
- `deploy.sh` / `deploy_windows.bat` install Node deps, build the frontend, then call the existing GCP deployment flow.
- `cloudbuild.yaml` deploys the same container; provide `_GEMINI_API_KEY` substitution or set GEMINI_API_KEY in the target environment.

## Folder guide
```
main.py                 # FastAPI app and endpoints (serves React SPA)
client/                 # React frontend (Vite, TypeScript)
  src/
    routes/
      LegalDocumentPage/  # Main legal document analysis page
requirements.txt        # Python dependencies
Dockerfile, app.yaml, cloudbuild.yaml
scripts/                # Helper scripts (frontend build helpers)
backup_frontend/        # Original Jinja2 templates (preserved for reference)
```

## Notes
- The UI is a custom React app designed specifically for legal document analysis
- Chat history shows previous Q&A and can be cleared per session
- PDF extraction uses PyPDF2's text; image-only PDFs won't be OCR'd
- Build the frontend with `npm run client:build` whenever static assets need to be refreshed

## Troubleshooting

### "API error: 400" or "Please check your GEMINI_API_KEY"
Your API key is either not set or invalid. Make sure you:
1. Get a valid API key from https://aistudio.google.com/app/apikey
2. Set it in your `.env` file or via `$env:GEMINI_API_KEY="your-key"`
3. Restart the server after setting the key

### Frontend not loading
Run `npm run client:build` to rebuild the frontend assets.
