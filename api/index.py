import sys
import os

# Add parent directory to path so we can import main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app as main_app
from fastapi import Request, FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

class PathRewriteMiddleware(BaseHTTPMiddleware):
    """Middleware to strip /api prefix from paths"""
    async def dispatch(self, request: Request, call_next):
        # Strip /api prefix if present
        path = request.url.path
        if path.startswith('/api/'):
            # Create new scope with rewritten path
            scope = dict(request.scope)
            scope['path'] = path[4:]  # Remove '/api'
            scope['raw_path'] = path[4:].encode()
            request = Request(scope, request.receive)
        
        response = await call_next(request)
        return response

# Add middleware to rewrite paths
main_app.add_middleware(PathRewriteMiddleware)

# Export the FastAPI app for Vercel
app = main_app