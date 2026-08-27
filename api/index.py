import sys
from pathlib import Path

# Ensure project root is in sys.path for Vercel Python serverless runtime
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.main import app
from mangum import Mangum

# Export FastAPI instance and Mangum Lambda adapter for Vercel Serverless
handler = Mangum(app, lifespan="off")
app = app
