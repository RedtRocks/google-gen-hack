
import uvicorn
import base64
import hashlib
import json
import os
import time
import random
import uuid
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlparse, urlunparse
from concurrent.futures import ThreadPoolExecutor
import threading
import google.generativeai as genai
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import PyPDF2
from io import BytesIO
import asyncpg
import asyncio
import logging
import re
from statistics import mean
from collections import Counter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Policy Reviewer API with Chat and Feedback System",
    description="Comprehensive API for analyzing policy documents using Gemini AI with chat functionality and feedback system",
    version="2.0.0"
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
DEFAULT_API_KEY = os.environ.get("GEMINI_API_KEY", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Global variables
db_pool = None
document_cache = {}
chat_history_cache = {}
analysis_progress = {}
batch_job_count = 0
retrieval_scores = []
retrieval_attempts = 0
retrieval_successes = 0
latency_log = []
error_count = 0
improvement_engine = None

# Thread pool with reduced size for Vercel
thread_pool = ThreadPoolExecutor(max_workers=1)

# Session with connection pooling
session = requests.Session()
retry_strategy = Retry(
    total=2,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
)
adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=5, pool_maxsize=5)
session.mount("http://", adapter)
session.mount("https://", adapter)

# ==================== MODELS ====================

class Location(BaseModel):
    continent: str
    countries: List[str]

class UseCase(BaseModel):
    category: str
    subCategories: List[str]

class PolicyAnalysisRequest(BaseModel):
    text: Optional[str] = None
    sector: str = "Technology"
    sub_sector: Optional[str] = None
    ai_usage: str = "Moderate"
    countries: List[str] = ["USA"]
    use_cases: Optional[str] = None
    api_key: Optional[str] = None

class AnalysisResponse(BaseModel):
    analysis: str
    request_id: str
    document_id: str
    raw_text: Optional[str] = None

class PolicyAnalysisFileRequest(BaseModel):
    files: List[UploadFile] = File([])
    storj_urls: Optional[List[str]] = Form(None)
    entityType: List[str] = []
    sector: str = "Technology"
    subSector: Optional[str] = None
    locations: List[Location] = []
    useCases: List[UseCase] = []
    user_id_uuid: Optional[str] = None
    context_id_uuid: Optional[str] = None
    org_id_uuid: Optional[str] = "default_context"
    api_key: Optional[str] = None
    batch_processing: bool = False
    max_concurrent: int = 5

class BatchAnalysisResponse(BaseModel):
    analyses: List[Dict[str, Any]]
    total_files: int
    successful_analyses: int
    failed_analyses: int
    batch_id: str

class ChatRequest(BaseModel):
    message: str
    document_ids: Optional[List[str]] = None
    session_id: Optional[str] = None
    sector: Optional[str] = "Technology"
    subsector: Optional[str] = None
    jurisdictions: List[str] = []
    roles: List[str] = ["consumer"]
    use_cases: List[str] = []
    locations: List[Location] = []
    useCases: List[UseCase] = []
    api_key: Optional[str] = None
    conversation_context: Optional[List[Dict[str, Any]]] = None
    system_role: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    document_ids: Optional[List[str]] = None
    conversation_context: List[Dict[str, Any]]
    assistant_response: List[Dict[str, Any]]

# Feedback Models
class FeedbackRequest(BaseModel):
    session_id: Optional[str] = None
    document_id: Optional[str] = None
    analysis_id: Optional[str] = None
    feedback_type: str  # 'rating', 'correction', 'suggestion', 'accuracy'
    rating: Optional[int] = None
    feedback_text: Optional[str] = None
    user_correction: Optional[str] = None
    feedback_category: str = "general"  # 'analysis_quality', 'accuracy', 'completeness', 'relevance'
    user_id_uuid: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}

class FeedbackResponse(BaseModel):
    feedback_id: int
    message: str
    improvements_suggested: Optional[List[str]] = None

class FeedbackAnalytics(BaseModel):
    total_feedback: int
    average_rating: float
    common_issues: List[Dict[str, Any]]
    improvement_suggestions: List[str]

# ==================== UTILITY FUNCTIONS ====================

def get_api_key(api_key: Optional[str] = None):
    """Get API key from environment variable or request"""
    return api_key or DEFAULT_API_KEY

def generate_unique_id():
    """Generate a unique request ID"""
    return f"req_{int(time.time())}_{hash(str(time.time()))}"[-12:]

def generate_session_id():
    """Generate a unique session ID"""
    return str(uuid.uuid4())

def generate_document_id():
    """Generate a unique document ID using UUID"""
    return str(uuid.uuid4())

def direct_api_call_optimized(prompt, api_key, max_retries=2):
    """Optimized API call with session reuse and retry logic"""
    if not api_key:
        raise ValueError("API key is required")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    max_prompt_length = 32000
    if len(prompt) > max_prompt_length:
        prompt = prompt[:max_prompt_length-100] + "..."
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4,
            "topP": 0.8,
            "topK": 40,
            "maxOutputTokens": 512,
            "stopSequences": []
        }
    }
    
    timeout = min(25, max(10, len(prompt) // 2000))
    
    for attempt in range(max_retries + 1):
        try:
            response = session.post(url, json=payload, headers=headers, timeout=timeout)
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    return result['candidates'][0]['content']['parts'][0]['text']
            
            if attempt < max_retries:
                time.sleep(0.5)
                continue
            else:
                return f"API error: {response.status_code}"
        except Exception as e:
            if attempt < max_retries:
                time.sleep(0.5)
                continue
            else:
                return f"API request failed: {str(e)}"
    
    return "API request failed after all retries"

def create_system_role(sector, subsector, jurisdictions, roles, use_cases):
    """Create system role configuration"""
    return {
        "sector": sector.lower().replace(" ", "-") if sector else "technology",
        "sectorReadable": sector or "Technology",
        "subsector": subsector.lower().replace(" ", "-") if subsector else "",
        "subsectorReadable": subsector or "",
        "jurisdictions": [j.lower() for j in jurisdictions] if jurisdictions else [],
        "jurisdictionReadable": ", ".join(jurisdictions) if jurisdictions else "",
        "roles": [r.lower() for r in roles] if roles else ["consumer"],
        "rolesReadable": ", ".join(roles) if roles else "Consumer",
        "useCases": use_cases or [],
        "useCasesReadable": ", ".join(use_cases) if use_cases else ""
    }

def format_locations(locations: List[Location]) -> str:
    formatted = []
    for loc in locations:
        countries = ", ".join(loc.countries)
        formatted.append(f"{loc.continent}: {countries}")
    return "\n    ".join(formatted)

def format_use_cases(use_cases: List[UseCase]) -> str:
    formatted = []
    for uc in use_cases:
        subcats = ", ".join(uc.subCategories)
        formatted.append(f"{uc.category}:\n      - {subcats}")
    return "\n    ".join(formatted)

# ==================== RAG PIPELINE ====================

class LightweightRAGPipeline:
    """Lightweight RAG pipeline with lazy loading"""
    def __init__(self):
        self.vectorizer = None
        self.document_vectors = None
        self.chunks = []
        self.chunk_metadata = []
        self.is_initialized = False
        self._sklearn_loaded = False

    def _load_sklearn(self):
        """Lazy load sklearn only when needed"""
        if not self._sklearn_loaded:
            try:
                global TfidfVectorizer, cosine_similarity
                from sklearn.feature_extraction.text import TfidfVectorizer
                from sklearn.metrics.pairwise import cosine_similarity
                self._sklearn_loaded = True
                return True
            except ImportError:
                logger.warning("sklearn not available, RAG features disabled")
                self._sklearn_loaded = False
                return False
        return True

    def initialize_model(self):
        """Initialize the TF-IDF vectorizer with lazy loading"""
        if not self.is_initialized:
            if self._load_sklearn():
                try:
                    self.vectorizer = TfidfVectorizer(
                        max_features=1000,
                        stop_words='english',
                        ngram_range=(1, 1),
                        min_df=1,
                        max_df=0.9
                    )
                    self.is_initialized = True
                    logger.info("Lightweight RAG model initialized successfully")
                except Exception as e:
                    logger.error(f"Failed to initialize RAG model: {str(e)}")
                    self.is_initialized = False
            else:
                logger.info("RAG features disabled - sklearn not available")
                self.is_initialized = False

    def chunk_text_for_rag(self, text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks for better retrieval"""
        if not text:
            return []
        
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < chunk_size:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks

    def add_document(self, document_id: str, text: str, metadata: dict = None):
        """Add a document to the RAG pipeline"""
        if not self.is_initialized:
            self.initialize_model()
        if not self.vectorizer:
            logger.warning("Vectorizer not available, skipping RAG indexing")
            return
        
        try:
            chunks = self.chunk_text_for_rag(text)
            for i, chunk in enumerate(chunks):
                self.chunks.append(chunk)
                self.chunk_metadata.append({
                    "document_id": document_id,
                    "chunk_index": i,
                    "metadata": metadata or {}
                })
            
            if self.chunks:
                self.document_vectors = self.vectorizer.fit_transform(self.chunks)
            
            logger.info(f"Added {len(chunks)} chunks from document {document_id} to RAG pipeline")
        except Exception as e:
            logger.error(f"Error adding document to RAG pipeline: {str(e)}")

    def retrieve_relevant_chunks(self, query: str, k: int = 3) -> List[Tuple[str, float, dict]]:
        """Retrieve most relevant chunks for a query"""
        global retrieval_attempts, retrieval_successes, retrieval_scores

        retrieval_attempts += 1

        if not self._sklearn_loaded:
            logger.warning("RAG features not available - sklearn not installed")
            return []

        if not self.is_initialized or not self.vectorizer or self.document_vectors is None:
            logger.warning("RAG pipeline not properly initialized")
            return []

        if not self._load_sklearn():
            return []

        try:
            query_vector = self.vectorizer.transform([query])
            similarities = cosine_similarity(query_vector, self.document_vectors)[0]
            top_indices = similarities.argsort()[-k:][::-1]

            results = []
            for idx in top_indices:
                if idx < len(self.chunks) and similarities[idx] > 0.1:
                    results.append((
                        self.chunks[idx],
                        float(similarities[idx]),
                        self.chunk_metadata[idx]
                    ))
                    retrieval_scores.append(float(similarities[idx]))

            if results:
                retrieval_successes += 1

            return results
        except Exception as e:
            logger.error(f"Error retrieving chunks: {str(e)}")
            return []

    def get_rag_context(self, query: str, max_context_length: int = 2000) -> str:
        """Get RAG context for a query"""
        if not self._sklearn_loaded:
            logger.warning("RAG features not available - sklearn not installed")
            return ""
        
        relevant_chunks = self.retrieve_relevant_chunks(query, k=3)
        if not relevant_chunks:
            return ""
        
        context_parts = []
        current_length = 0
        
        for chunk, score, metadata in relevant_chunks:
            if current_length + len(chunk) > max_context_length:
                break
            context_parts.append(f"[Relevance: {score:.3f}] {chunk}")
            current_length += len(chunk)
        
        return "\n\n".join(context_parts)

# Global RAG pipeline instance
rag_pipeline = LightweightRAGPipeline()

# ==================== FEEDBACK IMPROVEMENT ENGINE ====================

class FeedbackImprovementEngine:
    """Engine for automatically applying improvements based on feedback patterns"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.improvement_rules = {
            'low_rating_threshold': 2.5,
            'min_feedback_count': 5,
            'improvement_confidence_threshold': 0.7
        }
    
    async def run_periodic_improvements(self):
        """Run periodic improvement analysis and application"""
        try:
            logger.info("Starting periodic feedback improvement analysis")
            
            patterns = await self.analyze_feedback_patterns()
            improvements = await self.generate_pattern_based_improvements(patterns)
            applied_count = await self.apply_automatic_improvements(improvements)
            await self.update_performance_metrics(patterns)
            
            logger.info(f"Periodic improvement completed: {applied_count} improvements applied")
            
        except Exception as e:
            logger.error(f"Error in periodic improvement: {str(e)}")
    
    async def analyze_feedback_patterns(self):
        """Analyze patterns in user feedback"""
        async with self.db_pool.acquire() as conn:
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            patterns_query = """
            SELECT 
                feedback_category,
                feedback_type,
                rating,
                feedback_text,
                user_correction,
                COUNT(*) as frequency
            FROM feedback 
            WHERE created_at >= $1
            GROUP BY feedback_category, feedback_type, rating, feedback_text, user_correction
            HAVING COUNT(*) >= $2
            ORDER BY frequency DESC
            """
            
            patterns = await conn.fetch(
                patterns_query, 
                thirty_days_ago, 
                self.improvement_rules['min_feedback_count']
            )
            
            common_issues = await self.extract_common_issues(patterns)
            correction_patterns = await self.analyze_correction_patterns(conn)
            
            return {
                'patterns': patterns,
                'common_issues': common_issues,
                'corrections': correction_patterns,
                'analysis_date': datetime.utcnow()
            }
    
    async def extract_common_issues(self, patterns):
        """Extract common issues from feedback patterns"""
        issues = {
            'accuracy_issues': [],
            'completeness_issues': [],
            'relevance_issues': [],
            'format_issues': []
        }
        
        for pattern in patterns:
            category = pattern['feedback_category']
            text = pattern['feedback_text'] or ""
            
            if category == 'accuracy':
                if any(word in text.lower() for word in ['wrong', 'incorrect', 'false', 'mistake']):
                    issues['accuracy_issues'].append({
                        'text': text,
                        'frequency': pattern['frequency'],
                        'rating': pattern['rating']
                    })
            
            elif category == 'completeness':
                if any(word in text.lower() for word in ['missing', 'incomplete', 'more detail', 'expand']):
                    issues['completeness_issues'].append({
                        'text': text,
                        'frequency': pattern['frequency'],
                        'rating': pattern['rating']
                    })
            
            elif category == 'relevance':
                if any(word in text.lower() for word in ['not relevant', 'off-topic', 'irrelevant']):
                    issues['relevance_issues'].append({
                        'text': text,
                        'frequency': pattern['frequency'],
                        'rating': pattern['rating']
                    })
        
        return issues
    
    async def analyze_correction_patterns(self, conn):
        """Analyze user correction patterns to identify improvement opportunities"""
        corrections_query = """
        SELECT 
            user_correction,
            feedback_text,
            feedback_category,
            COUNT(*) as frequency
        FROM feedback 
        WHERE user_correction IS NOT NULL 
        AND user_correction != ''
        AND created_at >= $1
        GROUP BY user_correction, feedback_text, feedback_category
        ORDER BY frequency DESC
        LIMIT 20
        """
        
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        corrections = await conn.fetch(corrections_query, thirty_days_ago)
        
        correction_categories = {
            'factual_corrections': [],
            'tone_corrections': [],
            'structure_corrections': [],
            'scope_corrections': []
        }
        
        for correction in corrections:
            correction_text = correction['user_correction'].lower()
            
            if any(word in correction_text for word in ['actually', 'correct', 'should be', 'fact']):
                correction_categories['factual_corrections'].append(correction)
            elif any(word in correction_text for word in ['tone', 'professional', 'formal', 'casual']):
                correction_categories['tone_corrections'].append(correction)
            elif any(word in correction_text for word in ['structure', 'format', 'organize', 'order']):
                correction_categories['structure_corrections'].append(correction)
            elif any(word in correction_text for word in ['more', 'less', 'detail', 'brief', 'expand']):
                correction_categories['scope_corrections'].append(correction)
        
        return correction_categories
    
    async def generate_pattern_based_improvements(self, patterns):
        """Generate improvements based on identified patterns"""
        improvements = []
        
        for issue_type, issues in patterns['common_issues'].items():
            if issues:
                improvement = await self.create_improvement_for_issue_type(issue_type, issues)
                if improvement:
                    improvements.append(improvement)
        
        for correction_type, corrections in patterns['corrections'].items():
            if corrections:
                improvement = await self.create_improvement_for_corrections(correction_type, corrections)
                if improvement:
                    improvements.append(improvement)
        
        return improvements
    
    async def create_improvement_for_issue_type(self, issue_type, issues):
        """Create specific improvements for issue types"""
        if not issues:
            return None
        
        total_frequency = sum(issue['frequency'] for issue in issues)
        avg_rating = sum(issue['rating'] for issue in issues if issue['rating']) / len(issues)
        
        improvement_prompts = {
            'accuracy_issues': """
ACCURACY IMPROVEMENT GUIDELINES:
- Always double-check facts and figures before including them
- When uncertain about specific details, acknowledge the uncertainty
- Provide sources or indicate when information should be verified
- Be more conservative with definitive statements
- Cross-reference information when possible
            """,
            
            'completeness_issues': """
COMPLETENESS IMPROVEMENT GUIDELINES:
- Provide more comprehensive analysis covering all relevant aspects
- Include examples and practical applications where appropriate
- Address potential implications and considerations
- Expand on key points with additional context
- Ensure all parts of the user's question are addressed
            """,
            
            'relevance_issues': """
RELEVANCE IMPROVEMENT GUIDELINES:
- Stay focused on the specific context and requirements provided
- Prioritize information that directly relates to the user's sector and use case
- Avoid generic information that doesn't apply to the specific situation
- Tailor examples and recommendations to the stated context
- Filter out tangential information that doesn't add value
            """,
            
            'format_issues': """
FORMAT IMPROVEMENT GUIDELINES:
- Use clear headings and structure for better readability
- Organize information in logical sections
- Use bullet points and lists for better clarity
- Maintain consistent formatting throughout
- Ensure proper use of markdown formatting
            """
        }
        
        return {
            'type': issue_type,
            'prompt_addition': improvement_prompts.get(issue_type, ''),
            'confidence': min(total_frequency / 20.0, 1.0),
            'impact_score': (5.0 - avg_rating) / 5.0,
            'total_affected': total_frequency
        }
    
    async def create_improvement_for_corrections(self, correction_type, corrections):
        """Create improvements based on user corrections"""
        if not corrections:
            return None
        
        correction_prompts = {
            'factual_corrections': """
FACTUAL ACCURACY GUIDELINES:
- Verify all factual claims before including them
- Be explicit about uncertainty when information cannot be confirmed
- Use qualifying language for complex or evolving topics
- Provide context for statistics and data points
            """,
            
            'tone_corrections': """
TONE IMPROVEMENT GUIDELINES:
- Maintain a professional yet accessible tone
- Adapt formality level to the context and audience
- Be confident but not overly assertive
- Use clear, direct language while remaining respectful
            """,
            
            'structure_corrections': """
STRUCTURE IMPROVEMENT GUIDELINES:
- Use clear, logical organization with proper headings
- Present information in order of importance
- Use consistent formatting and structure
- Ensure smooth transitions between sections
            """,
            
            'scope_corrections': """
SCOPE IMPROVEMENT GUIDELINES:
- Provide appropriate level of detail for the context
- Balance comprehensiveness with brevity
- Focus on the most relevant information first
- Expand on critical points while avoiding unnecessary detail
            """
        }
        
        total_frequency = sum(correction['frequency'] for correction in corrections)
        
        return {
            'type': f"{correction_type}_improvement",
            'prompt_addition': correction_prompts.get(correction_type, ''),
            'confidence': min(total_frequency / 10.0, 1.0),
            'impact_score': 0.8,
            'total_affected': total_frequency
        }
    
    async def apply_automatic_improvements(self, improvements):
        """Apply high-confidence improvements automatically"""
        applied_count = 0
        
        for improvement in improvements:
            if improvement['confidence'] >= self.improvement_rules['improvement_confidence_threshold']:
                try:
                    await self.create_improved_prompt_entry(improvement)
                    applied_count += 1
                    logger.info(f"Applied automatic improvement: {improvement['type']}")
                except Exception as e:
                    logger.error(f"Error applying improvement {improvement['type']}: {str(e)}")
        
        return applied_count
    
    async def create_improved_prompt_entry(self, improvement):
        """Create an improved prompt entry in the database"""
        async with self.db_pool.acquire() as conn:
            query = """
            INSERT INTO prompt_improvements (
                original_prompt, improved_prompt, improvement_reason,
                feedback_ids, success_rate, is_active
            ) VALUES ($1, $2, $3, $4, $5, $6)
            """
            
            await conn.execute(
                query,
                "System-generated improvement",
                improvement['prompt_addition'],
                f"Automatic improvement based on {improvement['type']} patterns",
                [],
                improvement['confidence'],
                True
            )
    
    async def update_performance_metrics(self, patterns):
        """Update overall system performance metrics"""
        async with self.db_pool.acquire() as conn:
            total_feedback = len(patterns['patterns'])
            
            if total_feedback > 0:
                performance_query = """
                INSERT INTO model_performance (
                    analysis_type, average_rating, total_feedback_count,
                    improvement_suggestions, last_updated
                ) VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (analysis_type) DO UPDATE SET
                    average_rating = $2,
                    total_feedback_count = $3,
                    improvement_suggestions = $4,
                    last_updated = $5
                """
                
                ratings = [p['rating'] for p in patterns['patterns'] if p['rating']]
                avg_rating = sum(ratings) / len(ratings) if ratings else 3.0
                
                suggestions = []
                for issue_type, issues in patterns['common_issues'].items():
                    if issues:
                        suggestions.append(f"Address {issue_type.replace('_', ' ')}")
                
                await conn.execute(
                    performance_query,
                    "system_overall",
                    avg_rating,
                    total_feedback,
                    suggestions,
                    datetime.utcnow()
                )

# ==================== DATABASE FUNCTIONS ====================

async def init_db():
    """Initialize database connection pool with all required tables"""
    global db_pool
    if DATABASE_URL:
        try:
            db_pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=1,
                max_size=5,
                command_timeout=30,
                server_settings={
                    'application_name': 'policy_reviewer_api',
                    'search_path': 'public',
                }
            )
            logger.info("Database connection pool created successfully")
            
            async with db_pool.acquire() as conn:
                # Chat history table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS chat_history (
                        id SERIAL PRIMARY KEY,
                        session_id UUID UNIQUE NOT NULL,
                        conversation_context JSONB NOT NULL DEFAULT '[]',
                        assistant_response JSONB NOT NULL DEFAULT '[]',
                        system_role JSONB NOT NULL DEFAULT '{}',
                        document_ids VARCHAR(255)[],
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Policies table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS policies (
                        id SERIAL PRIMARY KEY,
                        storj_url TEXT UNIQUE,
                        document_id VARCHAR(255) NOT NULL,
                        analysis TEXT NOT NULL,
                        raw_text TEXT,
                        entityType JSONB,
                        sector VARCHAR(255),
                        subSector VARCHAR(255),
                        locations JSONB,
                        useCases JSONB,
                        created_at_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        user_id_uuid UUID,
                        context_id_uuid UUID,
                        org_id_uuid UUID,
                        metadata JSONB
                    )
                """)
                
                # Documents table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        id SERIAL PRIMARY KEY,
                        document_id VARCHAR(255) UNIQUE NOT NULL,
                        content TEXT NOT NULL,
                        metadata JSONB DEFAULT '{}',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Content hashes table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS content_hashes (
                        id SERIAL PRIMARY KEY,
                        content_hash VARCHAR(32) UNIQUE NOT NULL,
                        content_id VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Feedback table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS feedback (
                        id SERIAL PRIMARY KEY,
                        session_id UUID,
                        document_id VARCHAR(255),
                        analysis_id VARCHAR(255),
                        feedback_type VARCHAR(50) NOT NULL,
                        rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                        feedback_text TEXT,
                        user_correction TEXT,
                        feedback_category VARCHAR(100),
                        user_id_uuid UUID,
                        metadata JSONB DEFAULT '{}',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_processed BOOLEAN DEFAULT FALSE,
                        admin_response TEXT,
                        improvement_applied BOOLEAN DEFAULT FALSE
                    )
                """)
                
                # Feedback analytics table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS feedback_analytics (
                        id SERIAL PRIMARY KEY,
                        feedback_id INTEGER REFERENCES feedback(id),
                        sentiment_score DECIMAL(3,2),
                        key_issues JSONB,
                        suggested_improvements JSONB,
                        priority_level INTEGER DEFAULT 3,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Prompt improvements table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS prompt_improvements (
                        id SERIAL PRIMARY KEY,
                        original_prompt TEXT NOT NULL,
                        improved_prompt TEXT NOT NULL,
                        improvement_reason TEXT,
                        feedback_ids INTEGER[],
                        success_rate DECIMAL(5,2) DEFAULT 0.0,
                        usage_count INTEGER DEFAULT 0,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Model performance table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS model_performance (
                        id SERIAL PRIMARY KEY,
                        analysis_type VARCHAR(100) UNIQUE,
                        average_rating DECIMAL(3,2),
                        total_feedback_count INTEGER,
                        improvement_suggestions TEXT[],
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
        except Exception as e:
            logger.error(f"Error creating database connection pool: {str(e)}")
            db_pool = None

# ==================== HELPER FUNCTIONS ====================

def download_from_storj_url(url: str) -> bytes:
    """Download file content from URL with better error handling"""
    try:
        logger.info(f"Attempting to download from URL: {url[:100]}...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/pdf,application/octet-stream,*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        response = requests.get(url, timeout=60, headers=headers, stream=True)
        
        if response.status_code == 403:
            raise HTTPException(status_code=400, detail="Access denied. The presigned URL may have expired or is invalid.")
        elif response.status_code == 404:
            raise HTTPException(status_code=400, detail="File not found at the provided URL.")
        elif response.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Failed to download file. HTTP {response.status_code}: {response.reason}")
        
        response.raise_for_status()
        content = response.content
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Downloaded file is empty")
        
        logger.info(f"Successfully downloaded {len(content)} bytes")
        return content
        
    except Exception as e:
        logger.error(f"Error downloading from URL {url}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")

def extract_text_from_pdf_fast(pdf_bytes):
    """Faster PDF extraction with better error handling"""
    try:
        if not pdf_bytes or len(pdf_bytes) < 4:
            return "Invalid PDF file"
        
        text_parts = []
        pdf_file = BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        total_pages = len(pdf_reader.pages)
        
        MAX_PAGES = 50
        if total_pages > MAX_PAGES:
            logger.info(f"Limiting processing to first {MAX_PAGES} pages")
            total_pages = MAX_PAGES
        
        for page_num in range(total_pages):
            try:
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    cleaned_text = ' '.join(page_text.split())
                    text_parts.append(cleaned_text)
            except Exception as e:
                logger.warning(f"Error on page {page_num + 1}: {str(e)}")
                continue
        
        if not text_parts:
            return "No text extracted from PDF"
        
        full_text = "\n\n".join(text_parts)
        logger.info(f"Extracted {len(full_text)} characters from {total_pages} pages")
        return full_text
        
    except Exception as e:
        logger.error(f"PDF extraction error: {str(e)}")
        return f"PDF extraction failed: {str(e)}"

def smart_chunk_text(text, max_chunk_size=30000):
    """Smart chunking that preserves context"""
    if len(text) <= max_chunk_size:
        return [text]
    
    # Try to split by sections if available
    if "TABLE OF CONTENTS" in text.upper():
        sections = re.split(r'\n\s*(?:CHAPTER|SECTION|PART)\s+\d+', text)
        return [section.strip() for section in sections if len(section.strip()) > 1000]
    
    # Split by paragraphs
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        if len(current_chunk) + len(para) > max_chunk_size and current_chunk:
            chunks.append(current_chunk)
            current_chunk = para
        else:
            current_chunk += "\n\n" + para if current_chunk else para
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

def build_concise_prompt(request):
    """Build shorter, more focused prompt"""
    locations_summary = f"{len(request.locations)} regions"
    use_cases_summary = f"{len(request.useCases)} categories"
    
    return f"""Analyze this policy document for:
Entity Types: {', '.join(request.entityType)}
Sector: {request.sector} - {request.subSector or 'General'}
Locations: {locations_summary}
Use Cases: {use_cases_summary}

Provide concise analysis covering:
1. Key policy points
2. Impact on specified entities/sectors
3. Compliance requirements
4. Recommendations

Keep your response brief and to the point. Avoid extensive details."""

def setup_rag_for_document(document_id: str, text: str, metadata: dict = None):
    """Setup RAG pipeline for a document"""
    try:
        rag_pipeline.add_document(document_id, text, metadata)
        logger.info(f"RAG pipeline setup completed for document {document_id}")
    except Exception as e:
        logger.error(f"Failed to setup RAG for document {document_id}: {str(e)}")

# ==================== ANALYSIS FUNCTIONS ====================

async def analyze_with_feedback_improvements(text, prompt_context, api_key, request_id):
    """Enhanced analysis that incorporates feedback-based improvements"""
    try:
        # Get any applicable improved prompts
        if db_pool:
            async with db_pool.acquire() as conn:
                improved_prompt_query = """
                SELECT improved_prompt FROM prompt_improvements
                WHERE is_active = TRUE
                ORDER BY usage_count ASC, created_at DESC
                LIMIT 1
                """
                improved_prompt_row = await conn.fetchrow(improved_prompt_query)
                
                if improved_prompt_row:
                    # Use improved prompt and track usage
                    enhanced_prompt = f"{prompt_context}\n\n{improved_prompt_row['improved_prompt']}"
                    
                    # Update usage count
                    await conn.execute(
                        "UPDATE prompt_improvements SET usage_count = usage_count + 1 WHERE improved_prompt = $1",
                        improved_prompt_row['improved_prompt']
                    )
                    
                    return await analyze_large_document_fast(text, enhanced_prompt, api_key, request_id)
    
    except Exception as e:
        logger.error(f"Error using improved prompts: {str(e)}")
    
    # Fall back to original analysis
    return await analyze_large_document_fast(text, prompt_context, api_key, request_id)

async def analyze_large_document_fast(text, prompt_context, api_key, request_id):
    """Fast document analysis with parallel processing optimized for Vercel"""
    if len(text) < 50000:
        full_prompt = f"{prompt_context}\n\nDocument: {text}"
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(thread_pool, direct_api_call_optimized, full_prompt, api_key)
    
    chunks = smart_chunk_text(text, max_chunk_size=30000)
    
    if len(chunks) <= 3:
        chunk_analyses = await analyze_chunks_parallel(chunks, prompt_context, api_key)
        return "\n\n".join([f"## Section {i+1}\n{analysis}" for i, analysis in enumerate(chunk_analyses)])
    
    chunk_analyses = await analyze_chunks_parallel(chunks, prompt_context, api_key)
    combined_analysis = "\n\n".join([f"## Section {i+1}\n{analysis}"
                                   for i, analysis in enumerate(chunk_analyses)])
    
    synthesis_prompt = f"""Based on these section analyses, provide a brief synthesis:
    {combined_analysis[:6000]}...
    
    Provide: 1) Key summary 2) Main findings 3) Critical recommendations"""
    
    loop = asyncio.get_event_loop()
    final_synthesis = await loop.run_in_executor(thread_pool, direct_api_call_optimized, synthesis_prompt, api_key)
    
    return f"{combined_analysis}\n\n## Executive Summary\n{final_synthesis}"

async def analyze_chunks_parallel(chunks, prompt_context, api_key):
    """Analyze chunks in parallel with reduced concurrency for Vercel"""
    loop = asyncio.get_event_loop()
    tasks = []
    
    for i, chunk in enumerate(chunks):
        chunk_prompt = f"""
        {prompt_context}
        Part {i+1} of {len(chunks)}. Analyze this section:
        {chunk}
        """
        task = loop.run_in_executor(thread_pool, direct_api_call_optimized, chunk_prompt, api_key)
        tasks.append(task)
    
    batch_size = 3
    all_results = []
    
    for i in range(0, len(tasks), batch_size):
        batch = tasks[i:i + batch_size]
        batch_results = await asyncio.gather(*batch, return_exceptions=True)
        all_results.extend(batch_results)
        
        if i + batch_size < len(tasks):
            await asyncio.sleep(0.5)
    
    return [r for r in all_results if not isinstance(r, Exception)]

async def analyze_feedback_and_improve(feedback_id: int, request: FeedbackRequest, conn) -> List[str]:
    """Analyze feedback and suggest improvements"""
    improvements = []
    
    # Rating-based improvements
    if request.rating and request.rating <= 2:
        improvements.append("Low rating detected - review analysis quality")
        
        if request.user_correction:
            improvements.append("User correction available - update prompt templates")
            
    # Category-specific improvements
    if request.feedback_category == "accuracy":
        improvements.append("Accuracy issue - review fact-checking processes")
    elif request.feedback_category == "completeness":
        improvements.append("Completeness issue - expand analysis scope")
    elif request.feedback_category == "relevance":
        improvements.append("Relevance issue - improve context understanding")
    
    # Store analytics
    if improvements:
        analytics_query = """
        INSERT INTO feedback_analytics (
            feedback_id, key_issues, suggested_improvements, priority_level
        ) VALUES ($1, $2, $3, $4)
        """
        key_issues = {
            "rating": request.rating,
            "category": request.feedback_category,
            "has_correction": bool(request.user_correction)
        }
        priority = 1 if request.rating and request.rating <= 2 else 3
        
        await conn.execute(
            analytics_query,
            feedback_id,
            json.dumps(key_issues),
            json.dumps(improvements),
            priority
        )
    
    return improvements

# ==================== BACKGROUND TASKS ====================

async def process_feedback_improvements(feedback_id: int):
    """Background task to process feedback improvements"""
    try:
        if not db_pool:
            return
            
        async with db_pool.acquire() as conn:
            feedback_query = """
            SELECT f.*, fa.suggested_improvements 
            FROM feedback f
            LEFT JOIN feedback_analytics fa ON f.id = fa.feedback_id
            WHERE f.id = $1 AND f.is_processed = FALSE
            """
            feedback = await conn.fetchrow(feedback_query, feedback_id)
            
            if feedback and feedback["rating"] and feedback["rating"] <= 2:
                # Trigger reanalysis with improved prompts for low-rated content
                await trigger_reanalysis_with_improvements(feedback, conn)
                
    except Exception as e:
        logger.error(f"Error in background feedback processing: {str(e)}")

async def trigger_reanalysis_with_improvements(feedback, conn):
    """Trigger reanalysis using improved prompts"""
    try:
        prompt_query = """
        SELECT improved_prompt FROM prompt_improvements
        WHERE is_active = TRUE
        ORDER BY created_at DESC
        LIMIT 1
        """
        improved_prompt_row = await conn.fetchrow(prompt_query)
        
        if improved_prompt_row:
            logger.info(f"Would trigger reanalysis for feedback {feedback['id']} using improved prompt")
            
    except Exception as e:
        logger.error(f"Error triggering reanalysis: {str(e)}")

async def initialize_improvement_engine():
    """Initialize the improvement engine"""
    global improvement_engine
    if db_pool:
        improvement_engine = FeedbackImprovementEngine(db_pool)
        logger.info("Feedback improvement engine initialized")

async def run_scheduled_improvements():
    """Background task for scheduled improvements"""
    while True:
        try:
            if improvement_engine:
                await improvement_engine.run_periodic_improvements()
            
            # Run every 6 hours
            await asyncio.sleep(6 * 60 * 60)
            
        except Exception as e:
            logger.error(f"Error in scheduled improvements: {str(e)}")
            await asyncio.sleep(60 * 60)  # Wait 1 hour on error

# ==================== API ENDPOINTS ====================

@app.get("/")
async def root():
    return {"message": "Welcome to the Enhanced Policy Reviewer API with Chat and Feedback System. Visit /docs for API documentation."}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db_status = "connected" if db_pool else "not configured"
    return JSONResponse(content={
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_status,
        "cached_documents": len(document_cache),
        "cached_chat_sessions": len(chat_history_cache),
        "version": "2.0.0",
        "features": ["chat", "feedback_system", "rag_pipeline"]
    })

# ==================== CHAT ENDPOINTS ====================

@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_documents(request: ChatRequest):
    """Chat with analyzed documents using RAG pipeline"""
    api_key = get_api_key(request.api_key)
    if not api_key:
        raise HTTPException(status_code=400, detail="API key is required")
    
    # Generate session ID if not provided
    session_id = request.session_id or generate_session_id()
    
    try:
        # Load existing conversation context
        conversation_context = request.conversation_context or []
        
        # Get RAG context if document IDs are provided
        rag_context = ""
        if request.document_ids:
            query = request.message
            rag_context = rag_pipeline.get_rag_context(query, max_context_length=2000)
            
            # If no relevant context found, try to get document content from cache
            if not rag_context and request.document_ids:
                doc_contents = []
                for doc_id in request.document_ids:
                    if doc_id in document_cache:
                        doc_contents.append(document_cache[doc_id][:1000])  # First 1000 chars
                
                if doc_contents:
                    rag_context = "\n\n".join([f"Document Context:\n{content}" for content in doc_contents])
        
        # Create system role context
        system_role = request.system_role or create_system_role(
            request.sector,
            request.subsector, 
            request.jurisdictions,
            request.roles,
            request.use_cases
        )
        
        # Build enhanced prompt with context
        system_prompt = f"""You are a policy analysis assistant specializing in:
- Sector: {system_role.get('sectorReadable', 'General')}
- Subsector: {system_role.get('subsectorReadable', 'N/A')}
- Jurisdictions: {system_role.get('jurisdictionReadable', 'Global')}
- User Roles: {system_role.get('rolesReadable', 'General')}
- Use Cases: {system_role.get('useCasesReadable', 'General')}

Provide helpful, accurate, and contextually relevant responses about policy matters."""

        # Add RAG context if available
        if rag_context:
            enhanced_prompt = f"""{system_prompt}

Relevant Document Context:
{rag_context}

Based on the above context and conversation history, please respond to: {request.message}"""
        else:
            enhanced_prompt = f"""{system_prompt}

User Question: {request.message}"""
        
        # Add conversation history for context
        if conversation_context:
            history_text = "\n".join([
                f"{msg.get('role', 'user')}: {msg.get('content', '')}" 
                for msg in conversation_context[-5:]  # Last 5 messages
            ])
            enhanced_prompt = f"{enhanced_prompt}\n\nRecent Conversation:\n{history_text}"
        
        # Get AI response
        loop = asyncio.get_event_loop()
        ai_response = await loop.run_in_executor(
            thread_pool, 
            direct_api_call_optimized, 
            enhanced_prompt, 
            api_key
        )
        
        # Update conversation context
        conversation_context.append({
            "role": "user",
            "content": request.message,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        assistant_response = [{
            "role": "assistant", 
            "content": ai_response,
            "timestamp": datetime.utcnow().isoformat(),
            "rag_used": bool(rag_context),
            "document_ids": request.document_ids or []
        }]
        
        conversation_context.append(assistant_response[0])
        
        # Cache the session
        chat_history_cache[session_id] = {
            "conversation_context": conversation_context,
            "assistant_response": assistant_response,
            "system_role": system_role,
            "document_ids": request.document_ids or [],
            "last_updated": datetime.utcnow()
        }
        
        # Save to database if available
        if db_pool:
            try:
                async with db_pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO chat_history (
                            session_id, conversation_context, assistant_response, 
                            system_role, document_ids, updated_at
                        ) VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT (session_id) DO UPDATE SET
                            conversation_context = $2,
                            assistant_response = $3,
                            system_role = $4,
                            document_ids = $5,
                            updated_at = $6
                    """, 
                    uuid.UUID(session_id) if session_id else uuid.uuid4(),
                    json.dumps(conversation_context),
                    json.dumps(assistant_response),
                    json.dumps(system_role),
                    request.document_ids or [],
                    datetime.utcnow()
                    )
            except Exception as e:
                logger.error(f"Failed to save chat to database: {str(e)}")
        
        return JSONResponse(content={
            "response": ai_response,
            "session_id": session_id,
            "document_ids": request.document_ids,
            "conversation_context": conversation_context,
            "assistant_response": assistant_response,
            "rag_context_used": bool(rag_context),
            "system_role": system_role
        })
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

@app.get("/api/chat/{session_id}/history")
async def get_chat_history(session_id: str):
    """Get chat history for a session"""
    
    # Check cache first
    if session_id in chat_history_cache:
        return JSONResponse(content=chat_history_cache[session_id])
    
    # Check database
    if db_pool:
        try:
            async with db_pool.acquire() as conn:
                result = await conn.fetchrow(
                    "SELECT * FROM chat_history WHERE session_id = $1",
                    uuid.UUID(session_id)
                )
                if result:
                    history_data = {
                        "conversation_context": result["conversation_context"],
                        "assistant_response": result["assistant_response"], 
                        "system_role": result["system_role"],
                        "document_ids": result["document_ids"],
                        "last_updated": result["updated_at"].isoformat()
                    }
                    # Cache it
                    chat_history_cache[session_id] = history_data
                    return JSONResponse(content=history_data)
        except Exception as e:
            logger.error(f"Error fetching chat history: {str(e)}")
    
    raise HTTPException(status_code=404, detail="Chat session not found")

@app.delete("/api/chat/{session_id}")
async def delete_chat_session(session_id: str):
    """Delete a chat session"""
    
    # Remove from cache
    if session_id in chat_history_cache:
        del chat_history_cache[session_id]
    
    # Remove from database
    if db_pool:
        try:
            async with db_pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM chat_history WHERE session_id = $1",
                    uuid.UUID(session_id)
                )
                if result == "DELETE 0":
                    raise HTTPException(status_code=404, detail="Chat session not found")
        except Exception as e:
            logger.error(f"Error deleting chat session: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to delete chat session")
    
    return JSONResponse(content={"message": "Chat session deleted successfully"})

# ==================== FEEDBACK ENDPOINTS ====================

@app.post("/api/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    """Submit user feedback and trigger improvement analysis"""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database not available")
    
    try:
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                # Insert feedback
                query = """
                INSERT INTO feedback (
                    session_id, document_id, analysis_id, feedback_type,
                    rating, feedback_text, user_correction, feedback_category,
                    user_id_uuid, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING id
                """
                feedback_id = await conn.fetchval(
                    query,
                    request.session_id,
                    request.document_id,
                    request.analysis_id,
                    request.feedback_type,
                    request.rating,
                    request.feedback_text,
                    request.user_correction,
                    request.feedback_category,
                    request.user_id_uuid,
                    json.dumps(request.metadata)
                )
                
                # Analyze feedback and generate improvements
                improvements = await analyze_feedback_and_improve(
                    feedback_id, request, conn
                )
                
                # Trigger async improvement processing
                asyncio.create_task(process_feedback_improvements(feedback_id))
                
                return JSONResponse(content={
                    "feedback_id": feedback_id,
                    "message": "Feedback received and processed",
                    "improvements_suggested": improvements
                })
                
    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to submit feedback")

@app.get("/api/feedback/analytics", response_model=FeedbackAnalytics)
async def get_feedback_analytics():
    """Get feedback analytics and insights"""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database not available")
    
    try:
        async with db_pool.acquire() as conn:
            # Get overall stats
            stats_query = """
            SELECT 
                COUNT(*) as total_feedback,
                AVG(rating) as average_rating
            FROM feedback 
            WHERE rating IS NOT NULL
            """
            stats = await conn.fetchrow(stats_query)
            
            # Get common issues
            issues_query = """
            SELECT 
                feedback_category,
                COUNT(*) as count,
                AVG(rating) as avg_rating
            FROM feedback 
            GROUP BY feedback_category
            ORDER BY count DESC
            LIMIT 10
            """
            issues_rows = await conn.fetch(issues_query)
            
            common_issues = [
                {
                    "category": row["feedback_category"],
                    "count": row["count"],
                    "average_rating": float(row["avg_rating"]) if row["avg_rating"] else 0
                }
                for row in issues_rows
            ]
            
            # Get improvement suggestions
            improvements_query = """
            SELECT DISTINCT suggested_improvements
            FROM feedback_analytics
            WHERE suggested_improvements IS NOT NULL
            LIMIT 20
            """
            improvement_rows = await conn.fetch(improvements_query)
            improvement_suggestions = []
            for row in improvement_rows:
                if row["suggested_improvements"]:
                    improvement_suggestions.extend(row["suggested_improvements"])
            
            return JSONResponse(content={
                "total_feedback": stats["total_feedback"],
                "average_rating": float(stats["average_rating"]) if stats["average_rating"] else 0,
                "common_issues": common_issues,
                "improvement_suggestions": list(set(improvement_suggestions[:10]))
            })
            
    except Exception as e:
        logger.error(f"Error getting feedback analytics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get analytics")

@app.get("/api/feedback/improvement-insights")
async def get_improvement_insights():
    """Get insights about applied improvements and their effectiveness"""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database not available")
    
    try:
        async with db_pool.acquire() as conn:
            # Get improvement statistics
            improvements_query = """
            SELECT 
                improvement_reason,
                success_rate,
                usage_count,
                is_active,
                created_at
            FROM prompt_improvements
            ORDER BY created_at DESC
            LIMIT 20
            """
            improvements = await conn.fetch(improvements_query)
            
            # Get feedback trends
            trends_query = """
            SELECT 
                DATE(created_at) as date,
                AVG(rating) as avg_rating,
                COUNT(*) as feedback_count
            FROM feedback
            WHERE created_at >= $1
            GROUP BY DATE(created_at)
            ORDER BY date DESC
            LIMIT 30
            """
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            trends = await conn.fetch(trends_query, thirty_days_ago)
            
            # Get most effective improvements
            effective_improvements_query = """
            SELECT 
                improvement_reason,
                success_rate,
                usage_count
            FROM prompt_improvements
            WHERE is_active = TRUE
            ORDER BY (success_rate * usage_count) DESC
            LIMIT 10
            """
            effective_improvements = await conn.fetch(effective_improvements_query)
            
            return JSONResponse(content={
                "recent_improvements": [
                    {
                        "reason": imp["improvement_reason"],
                        "success_rate": float(imp["success_rate"]),
                        "usage_count": imp["usage_count"],
                        "is_active": imp["is_active"],
                        "created_at": imp["created_at"].isoformat()
                    }
                    for imp in improvements
                ],
                "feedback_trends": [
                    {
                        "date": trend["date"].isoformat(),
                        "average_rating": float(trend["avg_rating"]),
                        "feedback_count": trend["feedback_count"]
                    }
                    for trend in trends
                ],
                "most_effective_improvements": [
                    {
                        "reason": imp["improvement_reason"],
                        "success_rate": float(imp["success_rate"]),
                        "usage_count": imp["usage_count"]
                    }
                    for imp in effective_improvements
                ]
            })
            
    except Exception as e:
        logger.error(f"Error getting improvement insights: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get improvement insights")

@app.post("/api/admin/trigger-improvements")
async def trigger_manual_improvements():
    """Manually trigger improvement analysis and application"""
    if not improvement_engine:
        raise HTTPException(status_code=500, detail="Improvement engine not initialized")
    
    try:
        await improvement_engine.run_periodic_improvements()
        return JSONResponse(content={
            "message": "Improvement analysis completed successfully",
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Manual improvement trigger failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Improvement analysis failed")

# ==================== ANALYSIS ENDPOINTS ====================

@app.post("/api/analyze/text")
async def analyze_policy_text(request: PolicyAnalysisRequest):
    """Analyze policy text with feedback improvements"""
    if not request.text:
        raise HTTPException(status_code=400, detail="Text input is required")
    
    api_key = get_api_key(request.api_key)
    if not api_key:
        raise HTTPException(status_code=400, detail="API key is required")
    
    request_id = generate_unique_id()
    document_id = generate_document_id()
    document_cache[document_id] = request.text
    
    # Setup RAG for the document
    setup_rag_for_document(document_id, request.text)
    
    # Use feedback-enhanced analysis
    prompt = f"""Analyze the following policy document and provide a detailed review:
    Policy Document: {request.text}...
    Sector: {request.sector}
    Sub-sector: {request.sub_sector or "Not specified"}
    AI Usage Level: {request.ai_usage}
    Countries: {', '.join(request.countries)}
    Use Cases: {request.use_cases or "Not specified"}
    
    Please provide:
    1. A summary of the key points of the policy
    2. Analysis of the potential impacts
    3. Identification of any ambiguities or areas needing clarification
    4. Recommendations for improvement
    5. Compliance considerations
    
    Format your response in markdown with clear sections.
    """
    
    # Apply feedback improvements if available
    analysis_result = await analyze_with_feedback_improvements(
        request.text, prompt, api_key, request_id
    )
    
    return JSONResponse(content={
        "analysis": analysis_result,
        "request_id": request_id,
        "document_id": document_id,
        "raw_text": request.text[:1000] + "..." if len(request.text) > 1000 else request.text,
        "feedback_enhanced": True
    })

@app.post("/api/analyze/files")
async def analyze_policy_files(request: PolicyAnalysisFileRequest = Depends()):
    """Analyze policy files with feedback improvements"""
    api_key = get_api_key(request.api_key)
    if not api_key:
        raise HTTPException(status_code=400, detail="API key is required")
    
    if not request.files and not request.storj_urls:
        raise HTTPException(status_code=400, detail="Either files or storj_urls must be provided")
    
    analyses = []
    successful_analyses = 0
    failed_analyses = 0
    batch_id = generate_unique_id()
    
    # Process uploaded files
    if request.files:
        for file in request.files:
            try:
                if file.content_type != "application/pdf":
                    failed_analyses += 1
                    continue
                
                content = await file.read()
                text = extract_text_from_pdf_fast(content)
                
                if "extraction failed" in text.lower():
                    failed_analyses += 1
                    continue
                
                document_id = generate_document_id()
                document_cache[document_id] = text
                
                # Setup RAG for the document
                setup_rag_for_document(document_id, text, {
                    "filename": file.filename,
                    "sector": request.sector,
                    "subSector": request.subSector
                })
                
                # Build analysis prompt
                prompt = build_concise_prompt(request)
                
                # Apply feedback improvements
                analysis_result = await analyze_with_feedback_improvements(
                    text, prompt, api_key, f"{batch_id}_{file.filename}"
                )
                
                analyses.append({
                    "filename": file.filename,
                    "document_id": document_id,
                    "analysis": analysis_result,
                    "success": True
                })
                successful_analyses += 1
                
            except Exception as e:
                logger.error(f"Error processing file {file.filename}: {str(e)}")
                analyses.append({
                    "filename": file.filename,
                    "error": str(e),
                    "success": False
                })
                failed_analyses += 1
    
    # Process Storj URLs
    if request.storj_urls:
        for url in request.storj_urls:
            try:
                content = download_from_storj_url(url)
                text = extract_text_from_pdf_fast(content)
                
                if "extraction failed" in text.lower():
                    failed_analyses += 1
                    continue
                
                document_id = generate_document_id()
                document_cache[document_id] = text
                
                # Setup RAG for the document
                setup_rag_for_document(document_id, text, {
                    "url": url,
                    "sector": request.sector,
                    "subSector": request.subSector
                })
                
                # Build analysis prompt
                prompt = build_concise_prompt(request)
                
                # Apply feedback improvements
                analysis_result = await analyze_with_feedback_improvements(
                    text, prompt, api_key, f"{batch_id}_{url}"
                )
                
                analyses.append({
                    "url": url,
                    "document_id": document_id,
                    "analysis": analysis_result,
                    "success": True
                })
                successful_analyses += 1
                
            except Exception as e:
                logger.error(f"Error processing URL {url}: {str(e)}")
                analyses.append({
                    "url": url,
                    "error": str(e),
                    "success": False
                })
                failed_analyses += 1
    
    return JSONResponse(content={
        "analyses": analyses,
        "total_files": len(analyses),
        "successful_analyses": successful_analyses,
        "failed_analyses": failed_analyses,
        "batch_id": batch_id,
        "feedback_enhanced": True
    })

# ==================== DOCUMENT MANAGEMENT ENDPOINTS ====================

@app.get("/api/documents/{document_id}")
async def get_document(document_id: str):
    """Get document content and metadata"""
    if document_id in document_cache:
        return JSONResponse(content={
            "document_id": document_id,
            "content": document_cache[document_id][:1000] + "...",  # Truncated for display
            "full_length": len(document_cache[document_id]),
            "cached": True
        })
    
    if db_pool:
        try:
            async with db_pool.acquire() as conn:
                result = await conn.fetchrow(
                    "SELECT * FROM documents WHERE document_id = $1",
                    document_id
                )
                if result:
                    return JSONResponse(content={
                        "document_id": document_id,
                        "content": result["content"][:1000] + "...",  # Truncated for display
                        "full_length": len(result["content"]),
                        "metadata": result["metadata"],
                        "created_at": result["created_at"].isoformat(),
                        "cached": False
                    })
        except Exception as e:
            logger.error(f"Error fetching document: {str(e)}")
    
    raise HTTPException(status_code=404, detail="Document not found")

@app.get("/api/documents")
async def list_documents():
    """List all available documents"""
    documents = []
    
    # Add cached documents
    for doc_id in document_cache.keys():
        documents.append({
            "document_id": doc_id,
            "source": "cache",
            "length": len(document_cache[doc_id])
        })
    
    # Add database documents
    if db_pool:
        try:
            async with db_pool.acquire() as conn:
                results = await conn.fetch(
                    "SELECT document_id, metadata, created_at FROM documents ORDER BY created_at DESC"
                )
                for result in results:
                    documents.append({
                        "document_id": result["document_id"],
                        "source": "database",
                        "metadata": result["metadata"],
                        "created_at": result["created_at"].isoformat()
                    })
        except Exception as e:
            logger.error(f"Error listing documents: {str(e)}")
    
    return JSONResponse(content={
        "documents": documents,
        "total_count": len(documents)
    })

# ==================== SYSTEM MONITORING ENDPOINTS ====================

@app.get("/api/system/metrics")
async def get_system_metrics():
    """Get system performance metrics"""
    global retrieval_attempts, retrieval_successes, retrieval_scores, latency_log, error_count
    
    avg_latency = sum(latency_log[-100:]) / len(latency_log[-100:]) if latency_log else 0
    avg_retrieval_score = sum(retrieval_scores[-100:]) / len(retrieval_scores[-100:]) if retrieval_scores else 0
    retrieval_success_rate = (retrieval_successes / retrieval_attempts * 100) if retrieval_attempts > 0 else 0
    
    return JSONResponse(content={
        "system_health": {
            "database_connected": db_pool is not None,
            "rag_initialized": rag_pipeline.is_initialized,
            "improvement_engine_active": improvement_engine is not None
        },
        "performance_metrics": {
            "average_latency_ms": round(avg_latency, 2),
            "error_count": error_count,
            "cached_documents": len(document_cache),
            "cached_chat_sessions": len(chat_history_cache)
        },
        "rag_metrics": {
            "retrieval_attempts": retrieval_attempts,
            "retrieval_successes": retrieval_successes,
            "success_rate_percent": round(retrieval_success_rate, 2),
            "average_relevance_score": round(avg_retrieval_score, 3)
        },
        "timestamp": datetime.utcnow().isoformat()
    })

@app.post("/api/system/cleanup")
async def cleanup_system():
    """Manual system cleanup"""
    global document_cache, chat_history_cache, latency_log, retrieval_scores
    
    # Clear old cache entries
    if len(document_cache) > 50:
        items = list(document_cache.items())
        document_cache = dict(items[-25:])  # Keep last 25
    
    if len(chat_history_cache) > 100:
        items = list(chat_history_cache.items())
        chat_history_cache = dict(items[-50:])  # Keep last 50
    
    # Clear old metrics
    if len(latency_log) > 1000:
        latency_log = latency_log[-500:]  # Keep last 500
    
    if len(retrieval_scores) > 1000:
        retrieval_scores = retrieval_scores[-500:]  # Keep last 500
    
    return JSONResponse(content={
        "message": "System cleanup completed",
        "remaining_cached_documents": len(document_cache),
        "remaining_cached_sessions": len(chat_history_cache),
        "timestamp": datetime.utcnow().isoformat()
    })

# ==================== STARTUP/SHUTDOWN EVENTS ====================

@app.on_event("startup")
async def enhanced_startup_event():
    """Enhanced startup with improvement engine and feedback system"""
    await init_db()
    rag_pipeline.initialize_model()
    await initialize_improvement_engine()
    
    # Start background improvement task
    asyncio.create_task(run_scheduled_improvements())
    
    logger.info("Enhanced Policy Reviewer API with Chat and Feedback System started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup database connections on shutdown"""
    global db_pool
    if db_pool:
        await db_pool.close()
        logger.info("Database connection pool closed")

# ==================== MIDDLEWARE ====================

@app.middleware("http")
async def cleanup_middleware(request: Request, call_next):
    """Clean up memory after each request and track metrics"""
    start_time = time.time()
    response = await call_next(request)
    
    # Track latency
    latency_log.append((time.time() - start_time) * 1000)
    
    # Periodic cleanup
    if random.randint(1, 10) == 1:
        # Basic cleanup logic
        if len(document_cache) > 10:
            items = list(document_cache.items())
            document_cache = dict(items[-10:])
        
        if len(chat_history_cache) > 20:
            items = list(chat_history_cache.items())
            chat_history_cache = dict(items[-20:])
    
    return response

# ==================== EXCEPTION HANDLERS ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    global error_count
    error_count += 1
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler"""
    global error_count
    error_count += 1
    logger.error(f"Unexpected error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# ==================== MAIN ====================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
