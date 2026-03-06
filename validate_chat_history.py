import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.append(str(backend_path))

try:
    from app.routers import history, contexts, chat
    print("Routers imported successfully!")
    
    from app.main import app
    print("FastAPI app initialized successfully!")
    
except Exception as e:
    print(f"Error importing routers: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
