import sys
import os

# Add parent directory to path so we can import main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app as fastapi_app
from mangum import Mangum

# Wrap FastAPI with Mangum for AWS Lambda/Vercel compatibility
# Mangum handles the path rewriting automatically
handler = Mangum(fastapi_app, lifespan="off", api_gateway_base_path="/api")

# Vercel will look for 'handler' or 'app'
app = handler