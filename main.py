import uvicorn
import base64
import json
import os
import time
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
import google.generativeai as genai
import requests
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import PyPDF2
from io import BytesIO
import logging
import re
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env if present (dev convenience)
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Legal Document Demystifier",
    description="AI-powered tool to simplify complex legal documents into clear, accessible guidance",
    version="1.1.0"
)

# Mount frontend assets if available (skip for Vercel serverless)
if not os.environ.get("VERCEL"):
    FRONTEND_DIST_PATH = Path(__file__).parent / "client" / "dist"
    FRONTEND_ASSETS_PATH = FRONTEND_DIST_PATH / "assets"

    if FRONTEND_ASSETS_PATH.exists():
        app.mount("/assets", StaticFiles(directory=str(FRONTEND_ASSETS_PATH)), name="assets")
    else:
        logger.warning("Frontend assets not found at %s. Run `npm run client:build` to generate them.", FRONTEND_ASSETS_PATH)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_API_KEY":
    logger.warning("⚠️  GEMINI_API_KEY is not set or is a placeholder. Please set a valid API key to use the analysis features.")
    logger.warning("Get your API key from: https://aistudio.google.com/app/apikey")

# ==================== MODELS ====================

class DocumentAnalysisRequest(BaseModel):
    text: Optional[str] = None
    document_type: str = "contract"  # contract, agreement, terms, policy
    user_role: str = "individual"  # individual, business, tenant, borrower
    complexity_level: str = "simple"  # simple, detailed, expert

class DocumentAnalysisResponse(BaseModel):
    summary: str
    key_points: List[str]
    risks_and_concerns: List[str]
    recommendations: List[str]
    simplified_explanation: str
    document_id: str

class QuestionRequest(BaseModel):
    question: str
    document_id: Optional[str] = None
    document_text: Optional[str] = None

class QuestionResponse(BaseModel):
    answer: str
    relevant_sections: List[str]
    confidence_level: str

# ==================== UTILITY FUNCTIONS ====================

def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF file"""
    try:
        pdf_reader = PyPDF2.PdfReader(BytesIO(file_content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        logger.error(f"Error extracting PDF text: {str(e)}")
        return ""

def call_gemini_api(prompt: str, api_key: str) -> str:
    """Call Gemini API with the given prompt"""
    if not api_key:
        raise ValueError("Gemini API key is required")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.25,  # make responses more deterministic
            "topP": 0.85,
            "topK": 32,
            "maxOutputTokens": 2048,
        },
        # Safety settings can be added here if needed
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                return result['candidates'][0]['content']['parts'][0]['text']
        # Log detailed error for debugging
        error_detail = ""
        try:
            error_detail = response.json()
            logger.error(f"Gemini API error {response.status_code}: {error_detail}")
        except:
            logger.error(f"Gemini API error {response.status_code}: {response.text}")
        return f"API error: {response.status_code}. Please check your GEMINI_API_KEY is valid."
    except Exception as e:
        logger.error(f"API request failed: {str(e)}")
        return f"API request failed: {str(e)}"

def create_analysis_prompt(text: str, document_type: str, user_role: str, complexity_level: str) -> str:
    """Create a comprehensive analysis prompt for legal documents"""
    role_context = {
        "individual": "a regular person without legal expertise",
        "business": "a small business owner",
        "tenant": "someone looking to rent property",
        "borrower": "someone seeking a loan"
    }

    complexity_instructions = {
        "simple": "Use very simple language, avoid legal jargon, explain everything in everyday terms",
        "detailed": "Provide moderate detail with some legal terms explained in parentheses",
        "expert": "Include relevant legal terminology with explanations"
    }

    prompt = f"""You are a senior legal analyst assisting {role_context.get(user_role, 'a person')} in understanding a {document_type}.

QUALITY & STYLE DIRECTIVES:
1. {complexity_instructions.get(complexity_level, 'Use clear, simple language')}
2. NO hallucinations: only derive points present or strongly implied.
3. Each list item MUST be concise (≤180 chars) and start with an action or clear noun phrase.
4. Separate RISK vs NEUTRAL facts—do not mix.
5. If a section cannot be confidently derived, include one item: "Insufficient detail to assess".
6. Avoid hedging like "maybe" unless ambiguity exists and then state why.
7. Output ONLY raw JSON (no markdown fences / backticks).

DOCUMENT (truncated to 8k chars if long):
{text[:8000]}

Return STRICT JSON with EXACT keys:
{{
  "summary": "Clear purpose & scope (2-4 sentences, no marketing fluff).",
  "key_points": ["Concrete primary obligations / definitions / mechanisms"],
  "risks_and_concerns": ["Specific unfavorable clauses, asymmetries, penalties, vague areas"],
  "recommendations": ["Actionable next steps: clarify / negotiate / monitor"],
  "simplified_explanation": "Plain-language analogy / story style explanation"
}}

VALIDATION RULES:
- Valid JSON parseable by json.loads.
- No trailing commas, no comments, no markdown.
- Arrays 5–8 items (2–4 if very short document).

IF YOU CANNOT fully comply: still return syntactically valid JSON with best-effort fields."""
    return prompt

def create_question_prompt(question: str, document_text: str) -> str:
    """Create a prompt for answering specific questions about the document"""
    prompt = f"""You are a precise legal assistant.

DOCUMENT (truncated):
{document_text[:6000]}

QUESTION: {question}

Return ONLY JSON (no markdown) with keys:
{{
    "answer": "Direct, plain-language answer (avoid filler)",
    "relevant_sections": ["Verbatim supporting excerpts (short, trimmed)"],
    "confidence_level": "high" | "medium" | "low"
}}

RULES:
- If answer not clearly supported: confidence_level=\"low\" and explain uncertainty briefly.
- Each relevant_sections item ≤ 240 chars and MUST appear verbatim in the document.
- No invented clauses."""
    return prompt

# ==================== JSON PARSING UTILITIES ====================

JSON_CLEAN_PATTERN = re.compile(r"```(?:json)?(.*?)```", re.DOTALL | re.IGNORECASE)

def extract_json_block(raw: str) -> Optional[str]:
    """Attempt to extract a valid JSON object from a model response.
    Strategies:
    1. If fenced in markdown code blocks, take inside.
    2. Locate first '{' and last '}' and attempt parse progressively.
    3. Clean common artifacts (trailing backticks, stray commas before closing brackets).
    """
    if not raw:
        return None

    candidate = raw.strip()

    # 1. Markdown fence
    fenced = JSON_CLEAN_PATTERN.search(candidate)
    if fenced:
        candidate = fenced.group(1).strip()

    # 2. Narrow to outermost braces
    if candidate.count('{') and candidate.count('}'):
        first = candidate.find('{')
        last = candidate.rfind('}')
        candidate = candidate[first:last+1]

    # 3. Light sanitation: remove trailing commas before ] or }
    candidate = re.sub(r",(\s*[}\]])", r"\1", candidate)

    # 4. Try direct parse, if fail progressively shrink from end
    for _ in range(3):
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError as e:
            # Try trimming any trailing non-JSON noise
            candidate = candidate.rstrip('`\n\r ')
            if not candidate.endswith('}'):  # cannot fix easily
                break
    return None

def parse_analysis_response(raw: str) -> Optional[Dict[str, Any]]:
    """Parse raw model output into structured dict if possible."""
    block = extract_json_block(raw)
    if not block:
        return None
    try:
        data = json.loads(block)
    except Exception:
        return None

    # Basic schema correction
    required_keys = {"summary", "key_points", "risks_and_concerns", "recommendations", "simplified_explanation"}
    for k in required_keys:
        data.setdefault(k, "" if k in {"summary", "simplified_explanation"} else [])
    # Normalize list fields
    for list_key in ["key_points", "risks_and_concerns", "recommendations"]:
        if not isinstance(data.get(list_key), list):
            data[list_key] = [str(data.get(list_key, ""))] if data.get(list_key) else []
    return data

def parse_question_response(raw: str) -> Optional[Dict[str, Any]]:
    block = extract_json_block(raw)
    if not block:
        return None
    try:
        data = json.loads(block)
    except Exception:
        return None
    # Fill defaults
    data.setdefault("answer", "")
    if not isinstance(data.get("relevant_sections"), list):
        data["relevant_sections"] = [str(data.get("relevant_sections", ""))] if data.get("relevant_sections") else []
    data.setdefault("confidence_level", "low")
    return data


# Global storage for documents and chat history (in production, use a proper database)
document_storage = {}
chat_history_storage = {}  # {session_id: [ {question, answer, relevant_sections, confidence_level, timestamp} ] }

# ==================== API ENDPOINTS ====================

def get_session_id(request: Request):
    # Use cookie or fallback to IP for demo; in production use real session/user auth
    session_id = request.cookies.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
    return session_id

@app.post("/save-chat", response_class=JSONResponse)
async def save_chat(request: Request):
    data = await request.json()
    session_id = get_session_id(request)
    chat = {
        "question": data.get("question"),
        "answer": data.get("answer"),
        "relevant_sections": data.get("relevant_sections", []),
        "confidence_level": data.get("confidence_level", ""),
        "timestamp": int(time.time())
    }
    chat_history_storage.setdefault(session_id, []).append(chat)
    return {"status": "ok"}

@app.get("/chat-history", response_class=JSONResponse)
async def chat_history(request: Request):
    session_id = get_session_id(request)
    history = chat_history_storage.get(session_id, [])
    return {"chats": history}

@app.post("/clear-chat-history", response_class=JSONResponse)
async def clear_chat_history(request: Request):
    """Clear chat history for current session"""
    session_id = get_session_id(request)
    if session_id in chat_history_storage:
        chat_history_storage[session_id] = []
    return {"success": True}

# ==================== API ENDPOINTS ====================

def _frontend_index_response() -> FileResponse:
    index_path = FRONTEND_DIST_PATH / "index.html"
    if not index_path.exists():
        logger.error("Frontend index not found at %s", index_path)
        raise HTTPException(status_code=500, detail="Frontend build missing. Please run npm run client:build")
    return FileResponse(str(index_path))


@app.post("/analyze-document", response_model=DocumentAnalysisResponse)
async def analyze_document(
    file: UploadFile = File(...),
    document_type: str = Form("contract"),
    user_role: str = Form("individual"),
    complexity_level: str = Form("simple")
):
    """Analyze an uploaded legal document"""
    
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API key not configured")
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Extract text based on file type
        if file.filename.lower().endswith('.pdf'):
            text = extract_text_from_pdf(file_content)
        else:
            text = file_content.decode('utf-8', errors='ignore')
        
        if not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from the document")
        
        # Generate document ID
        document_id = str(uuid.uuid4())
        
        # Store document for future questions
        document_storage[document_id] = text
        
        # Create analysis prompt
        prompt = create_analysis_prompt(text, document_type, user_role, complexity_level)
        
        # Call Gemini API
        response = call_gemini_api(prompt, GEMINI_API_KEY)

        parsed = parse_analysis_response(response)
        if parsed:
            return DocumentAnalysisResponse(document_id=document_id, **parsed)
        else:
            logger.warning("Falling back – could not parse JSON analysis")
            return DocumentAnalysisResponse(
                document_id=document_id,
                summary="Automated analysis generated but JSON formatting failed.",
                key_points=["Retry may yield structured output", "Model returned unstructured text"],
                risks_and_concerns=["Parsing failure prevented deeper extraction"],
                recommendations=["Re-run analysis", "Consider shortening or simplifying upload"],
                simplified_explanation=response[:600] + ("..." if len(response) > 600 else "")
            )
            
    except Exception as e:
        logger.error(f"Error analyzing document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.post("/analyze-text", response_model=DocumentAnalysisResponse)
async def analyze_text(request: DocumentAnalysisRequest):
    """Analyze legal document text directly"""
    
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API key not configured")
    
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Document text is required")
    
    try:
        # Generate document ID
        document_id = str(uuid.uuid4())
        
        # Store document for future questions
        document_storage[document_id] = request.text
        
        # Create analysis prompt
        prompt = create_analysis_prompt(
            request.text, 
            request.document_type, 
            request.user_role, 
            request.complexity_level
        )
        
        # Call Gemini API
        response = call_gemini_api(prompt, GEMINI_API_KEY)
        parsed = parse_analysis_response(response)
        if parsed:
            return DocumentAnalysisResponse(document_id=document_id, **parsed)
        else:
            logger.warning("Falling back – could not parse JSON analysis (text endpoint)")
            return DocumentAnalysisResponse(
                document_id=document_id,
                summary="Automated analysis generated but JSON formatting failed.",
                key_points=["Retry may yield structured output", "Model returned unstructured text"],
                risks_and_concerns=["Parsing failure prevented deeper extraction"],
                recommendations=["Re-run analysis", "Consider reducing document length"],
                simplified_explanation=response[:600] + ("..." if len(response) > 600 else "")
            )
            
    except Exception as e:
        logger.error(f"Error analyzing text: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.post("/ask-question", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """Ask a specific question about a legal document"""
    
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API key not configured")
    
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question is required")
    
    # Get document text
    document_text = ""
    if request.document_id and request.document_id in document_storage:
        document_text = document_storage[request.document_id]
    elif request.document_text:
        document_text = request.document_text
    else:
        raise HTTPException(status_code=400, detail="Document ID or text is required")
    
    try:
        # Create question prompt
        prompt = create_question_prompt(request.question, document_text)
        
        # Call Gemini API
        response = call_gemini_api(prompt, GEMINI_API_KEY)
        parsed = parse_question_response(response)
        if parsed:
            return QuestionResponse(**parsed)
        else:
            logger.warning("Falling back – could not parse JSON question response")
            return QuestionResponse(
                answer=response[:500] + ("..." if len(response) > 500 else ""),
                relevant_sections=["Unstructured answer returned"],
                confidence_level="low"
            )
            
    except Exception as e:
        logger.error(f"Error answering question: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Question processing failed: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/", response_class=HTMLResponse)
async def root(_: Request):
    """Serve the main application page (SPA entry point)"""
    return _frontend_index_response()

@app.get("/{full_path:path}", response_class=HTMLResponse)
async def spa_fallback(full_path: str):
    """Serve SPA index for client-side routes while preserving API paths."""
    # This catches all unmatched routes and serves the frontend
    return _frontend_index_response()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)