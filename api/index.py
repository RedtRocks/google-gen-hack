from mangum import Mangum
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app as fastapi_app

# Create Mangum handler - Vercel will call this
handler = Mangum(fastapi_app, lifespan="off", api_gateway_base_path="/api")

# Vercel looks for 'handler' or 'app'
app = handler