"""
Vercel serverless function entry point for FastAPI app
Uses Mangum to adapt FastAPI (ASGI) to Vercel's serverless format
"""
import sys
from pathlib import Path

# Add the parent directory to Python path
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

# Import Mangum and FastAPI app
from mangum import Mangum
from main import app as fastapi_app

# Create Mangum handler
# Mangum adapts ASGI apps to work with AWS Lambda/Vercel
handler = Mangum(fastapi_app, lifespan="off")

# Export as 'app' for Vercel
app = handler