import sys
import os

# Add parent directory to path so we can import main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

# Export the FastAPI app as 'app' for Vercel
# Vercel will wrap this with mangum automatically
app = app