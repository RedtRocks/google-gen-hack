"""
Analyze text endpoint for Vercel
Routes /api/analyze-text to FastAPI's /analyze-text
"""
import sys
import os
from pathlib import Path

# Set VERCEL environment variable
os.environ["VERCEL"] = "1"

# Add parent directory to path
parent_dir = str(Path(__file__).resolve().parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import Mangum and FastAPI app
from mangum import Mangum
from main import app as fastapi_app

# Create handler with base path
handler = Mangum(fastapi_app, lifespan="off", api_gateway_base_path="/api")
app = handler
