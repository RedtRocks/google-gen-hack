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
from pydantic import BaseModel
import PyPDF2
from io import BytesIO
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Legal Document Demystifier",
    description="AI-powered tool to simplify complex legal documents into clear, accessible guidance",
    version="1.0.0"
)

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
async def root():
    """Serve the main application page"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Legal Document Demystifier</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
            .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #2c3e50; text-align: center; margin-bottom: 30px; }
            .upload-section { border: 2px dashed #3498db; padding: 30px; text-align: center; margin: 20px 0; border-radius: 10px; }
            .form-group { margin: 15px 0; }
            label { display: block; margin-bottom: 5px; font-weight: bold; color: #34495e; }
            select, textarea, input[type="file"] { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
            button { background: #3498db; color: white; padding: 12px 30px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
            button:hover { background: #2980b9; }
            .results { margin-top: 30px; padding: 20px; background: #ecf0f1; border-radius: 10px; }
            .section { margin: 20px 0; padding: 15px; background: white; border-radius: 5px; border-left: 4px solid #3498db; }
            .risk { border-left-color: #e74c3c; }
            .recommendation { border-left-color: #27ae60; }
            .question-section { margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 10px; }
            .loading { text-align: center; color: #7f8c8d; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏛️ Legal Document Demystifier</h1>
            <p style="text-align: center; color: #7f8c8d; font-size: 18px;">
                Upload your legal document and get clear, simple explanations in plain English
            </p>
            
            <div class="upload-section">
                <h3>📄 Upload Your Document</h3>
                <form id="uploadForm" enctype="multipart/form-data">
                    <div class="form-group">
                        <input type="file" id="fileInput" accept=".pdf,.txt,.doc,.docx" required>
                    </div>
                    
                    <div class="form-group">
                        <label>Or paste your document text:</label>
                        <textarea id="textInput" rows="6" placeholder="Paste your legal document text here..."></textarea>
                    </div>
                    
                    <div style="display: flex; gap: 20px; margin: 20px 0;">
                        <div class="form-group" style="flex: 1;">
                            <label>Document Type:</label>
                            <select id="documentType">
                                <option value="contract">Contract</option>
                                <option value="rental_agreement">Rental Agreement</option>
                                <option value="loan_agreement">Loan Agreement</option>
                                <option value="terms_of_service">Terms of Service</option>
                                <option value="privacy_policy">Privacy Policy</option>
                                <option value="employment_contract">Employment Contract</option>
                                <option value="other">Other</option>
                            </select>
                        </div>
                        
                        <div class="form-group" style="flex: 1;">
                            <label>Your Role:</label>
                            <select id="userRole">
                                <option value="individual">Individual/Consumer</option>
                                <option value="business">Small Business Owner</option>
                                <option value="tenant">Tenant/Renter</option>
                                <option value="borrower">Borrower</option>
                                <option value="employee">Employee</option>
                            </select>
                        </div>
                        
                        <div class="form-group" style="flex: 1;">
                            <label>Explanation Level:</label>
                            <select id="complexityLevel">
                                <option value="simple">Simple (No legal jargon)</option>
                                <option value="detailed">Detailed (Some legal terms)</option>
                                <option value="expert">Expert (Full legal context)</option>
                            </select>
                        </div>
                    </div>
                    
                    <button type="submit">🔍 Analyze Document</button>
                </form>
            </div>
            
            <div id="results" style="display: none;"></div>
            
            <div id="questionSection" class="question-section" style="display: none;">
                <h3>❓ Ask Questions About Your Document</h3>
                <div class="form-group">
                    <textarea id="questionInput" rows="3" placeholder="Ask any question about your document..."></textarea>
                </div>
                <button onclick="askQuestion()">Get Answer</button>
                <div id="questionResults"></div>
            </div>
        </div>

        <script>
            let currentDocumentId = null;
            let currentDocumentText = null;

            document.getElementById('uploadForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const fileInput = document.getElementById('fileInput');
                const textInput = document.getElementById('textInput').value;
                const documentType = document.getElementById('documentType').value;
                const userRole = document.getElementById('userRole').value;
                const complexityLevel = document.getElementById('complexityLevel').value;
                
                if (!fileInput.files[0] && !textInput) {
                    alert('Please upload a file or paste document text');
                    return;
                }
                
                const resultsDiv = document.getElementById('results');
                resultsDiv.style.display = 'block';
                resultsDiv.innerHTML = '<div class="loading">🔄 Analyzing your document... This may take a moment.</div>';
                
                try {
                    let response;
                    
                    if (fileInput.files[0]) {
                        const formData = new FormData();
                        formData.append('file', fileInput.files[0]);
                        formData.append('document_type', documentType);
                        formData.append('user_role', userRole);
                        formData.append('complexity_level', complexityLevel);
                        
                        response = await fetch('/analyze-document', {
                            method: 'POST',
                            body: formData
                        });
                    } else {
                        response = await fetch('/analyze-text', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                text: textInput,
                                document_type: documentType,
                                user_role: userRole,
                                complexity_level: complexityLevel
                            })
                        });
                    }
                    
                    const result = await response.json();
                    
                    if (response.ok) {
                        currentDocumentId = result.document_id;
                        currentDocumentText = textInput || 'Uploaded file content';
                        displayResults(result);
                        document.getElementById('questionSection').style.display = 'block';
                    } else {
                        resultsDiv.innerHTML = `<div style="color: red;">Error: ${result.detail || 'Analysis failed'}</div>`;
                    }
                } catch (error) {
                    resultsDiv.innerHTML = `<div style="color: red;">Error: ${error.message}</div>`;
                }
            });
            
            function displayResults(result) {
                const resultsDiv = document.getElementById('results');
                
                resultsDiv.innerHTML = `
                    <h2>📋 Document Analysis Results</h2>
                    
                    <div class="section">
                        <h3>📝 Summary</h3>
                        <p>${result.summary}</p>
                    </div>
                    
                    <div class="section">
                        <h3>🔑 Key Points</h3>
                        <ul>
                            ${result.key_points.map(point => `<li>${point}</li>`).join('')}
                        </ul>
                    </div>
                    
                    <div class="section risk">
                        <h3>⚠️ Risks & Concerns</h3>
                        <ul>
                            ${result.risks_and_concerns.map(risk => `<li>${risk}</li>`).join('')}
                        </ul>
                    </div>
                    
                    <div class="section recommendation">
                        <h3>💡 Recommendations</h3>
                        <ul>
                            ${result.recommendations.map(rec => `<li>${rec}</li>`).join('')}
                        </ul>
                    </div>
                    
                    <div class="section">
                        <h3>🗣️ In Simple Terms</h3>
                        <p>${result.simplified_explanation}</p>
                    </div>
                `;
            }
            
            async function askQuestion() {
                const questionInput = document.getElementById('questionInput');
                const question = questionInput.value.trim();
                
                if (!question) {
                    alert('Please enter a question');
                    return;
                }
                
                const resultsDiv = document.getElementById('questionResults');
                resultsDiv.innerHTML = '<div class="loading">🤔 Finding the answer...</div>';
                
                try {
                    const response = await fetch('/ask-question', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            question: question,
                            document_id: currentDocumentId,
                            document_text: currentDocumentText
                        })
                    });
                    
                    const result = await response.json();
                    
                    if (response.ok) {
                        resultsDiv.innerHTML = `
                            <div class="section">
                                <h4>💬 Answer</h4>
                                <p>${result.answer}</p>
                                
                                <h4>📄 Relevant Sections</h4>
                                <ul>
                                    ${result.relevant_sections.map(section => `<li><em>"${section}"</em></li>`).join('')}
                                </ul>
                                
                                <p><small>Confidence Level: ${result.confidence_level}</small></p>
                            </div>
                        `;
                        questionInput.value = '';
                    } else {
                        resultsDiv.innerHTML = `<div style="color: red;">Error: ${result.detail}</div>`;
                    }
                } catch (error) {
                    resultsDiv.innerHTML = `<div style="color: red;">Error: ${error.message}</div>`;
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

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