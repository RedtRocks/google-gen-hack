"""
Vercel serverless function for FastAPI
Using Mangum adapter for AWS Lambda compatibility
"""
from mangum import Mangum
import sys
import os
from pathlib import Path

# Set VERCEL environment variable
os.environ["VERCEL"] = "1"

# Add parent directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import FastAPI app
from main import app as fastapi_app

# Create handler with Mangum
handler = Mangum(fastapi_app, lifespan="off")

# Vercel requires 'app' or 'handler'
app = handler