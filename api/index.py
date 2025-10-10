"""
Vercel serverless function for FastAPI
This handles ALL API endpoints through FastAPI
"""
from mangum import Mangum
import sys
import os
from pathlib import Path

# Set VERCEL environment variable
os.environ["VERCEL"] = "1"

# Add parent directory to sys.path to import main
parent_dir = str(Path(__file__).resolve().parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import FastAPI app
from main import app as fastapi_app

# Create Mangum handler
# api_gateway_base_path tells Mangum that requests come with /api prefix
# which it should strip before passing to FastAPI
handler = Mangum(fastapi_app, lifespan="off", api_gateway_base_path="/api")

# Export for Vercel
app = handler