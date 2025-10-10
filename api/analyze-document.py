"""
Analyze document endpoint for Vercel
Routes /api/analyze-document to FastAPI's /analyze-document
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

# Create handler with base path to strip /api prefix
# When Vercel routes /api/analyze-document here, Mangum strips /api
# and FastAPI sees /analyze-document
handler = Mangum(fastapi_app, lifespan="off", api_gateway_base_path="/api")
app = handler
