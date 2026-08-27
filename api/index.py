import sys
import traceback
from pathlib import Path

# Ensure project root and backend dir are in sys.path
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"
for d in [str(root_dir), str(backend_dir)]:
    if d not in sys.path:
        sys.path.insert(0, d)

try:
    from backend.main import app
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
except Exception as e:
    err_trace = traceback.format_exc()
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    from mangum import Mangum
    app = FastAPI()
    
    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    async def serverless_error_fallback(path: str):
        return JSONResponse({
            "status": "error",
            "message": "Vercel Python backend failed during module initialization",
            "traceback": err_trace
        }, status_code=500)
        
    handler = Mangum(app, lifespan="off")
