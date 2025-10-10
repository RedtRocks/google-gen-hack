"""
Clean FastAPI app export for Vercel serverless environment
This file exports the FastAPI app without any filesystem operations
"""
import os
os.environ["VERCEL"] = "1"  # Set this before importing main

# Now import the app
from main import app

# Export for Vercel
__all__ = ["app"]
