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
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from pydantic import BaseModel
import PyPDF2
from io import BytesIO
import logging
import re
from dotenv import load_dotenv

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

# Mount static files & templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

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
            "temperature": 0.3,
            "topP": 0.8,
            "topK": 40,
            "maxOutputTokens": 2048,
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                return result['candidates'][0]['content']['parts'][0]['text']
        return f"API error: {response.status_code}"
    except Exception as e:
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
    
    prompt = f"""
You are a legal document expert helping {role_context.get(user_role, 'a person')} understand a {document_type}.

INSTRUCTIONS:
- {complexity_instructions.get(complexity_level, 'Use clear, simple language')}
- Focus on practical implications and real-world consequences
- Highlight potential risks and red flags
- Provide actionable recommendations
- Be empathetic and supportive in tone

DOCUMENT TEXT:
{text[:8000]}  # Limit text length

Please provide a comprehensive analysis in the following JSON format:
{{
    "summary": "A clear, concise summary of what this document is about and its main purpose",
    "key_points": [
        "List of 5-7 most important points from the document",
        "Each point should be in plain English",
        "Focus on what matters most to the user"
    ],
    "risks_and_concerns": [
        "Potential risks or unfavorable terms",
        "Things the user should be careful about",
        "Red flags or concerning clauses"
    ],
    "recommendations": [
        "Specific actions the user should take",
        "Questions they should ask",
        "Things to negotiate or clarify"
    ],
    "simplified_explanation": "A paragraph explaining the document as if talking to a friend, using analogies and simple examples where helpful"
}}

Respond ONLY with valid JSON.
"""
    return prompt

def create_question_prompt(question: str, document_text: str) -> str:
    """Create a prompt for answering specific questions about the document"""
    
    prompt = f"""
You are a helpful legal assistant. A user has a question about their legal document.

DOCUMENT TEXT:
{document_text[:6000]}

USER QUESTION:
{question}

Please provide a helpful answer in the following JSON format:
{{
    "answer": "A clear, helpful answer to the user's question in simple language",
    "relevant_sections": [
        "Specific quotes or sections from the document that relate to the question",
        "Include the actual text that supports your answer"
    ],
    "confidence_level": "high/medium/low - how confident you are in this answer"
}}

Guidelines:
- Use simple, non-legal language
- Be specific and practical
- If you're not certain, say so
- Focus on what this means for the user personally

Respond ONLY with valid JSON.
"""
    return prompt

# Global storage for documents (in production, use a proper database)
document_storage = {}

# ==================== API ENDPOINTS ====================

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main application page (templated UI)"""
    return templates.TemplateResponse("index.html", {"request": request})

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
        
        # Parse JSON response
        try:
            analysis_data = json.loads(response)
            return DocumentAnalysisResponse(
                document_id=document_id,
                **analysis_data
            )
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return DocumentAnalysisResponse(
                document_id=document_id,
                summary="Analysis completed but formatting error occurred",
                key_points=["Please try again or contact support"],
                risks_and_concerns=["Unable to parse detailed analysis"],
                recommendations=["Please re-upload the document"],
                simplified_explanation=response[:500] + "..."
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
        
        # Parse JSON response
        try:
            analysis_data = json.loads(response)
            return DocumentAnalysisResponse(
                document_id=document_id,
                **analysis_data
            )
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return DocumentAnalysisResponse(
                document_id=document_id,
                summary="Analysis completed but formatting error occurred",
                key_points=["Please try again or contact support"],
                risks_and_concerns=["Unable to parse detailed analysis"],
                recommendations=["Please try with different text"],
                simplified_explanation=response[:500] + "..."
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
        
        # Parse JSON response
        try:
            question_data = json.loads(response)
            return QuestionResponse(**question_data)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return QuestionResponse(
                answer=response[:500] + "...",
                relevant_sections=["Could not parse structured response"],
                confidence_level="low"
            )
            
    except Exception as e:
        logger.error(f"Error answering question: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Question processing failed: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)