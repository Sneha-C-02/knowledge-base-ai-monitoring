import os
import sys

# Ensure the backend root directory is in sys.path
backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from src.knowledge_base_backend.bootstrap.application_factory import create_application

app = create_application()
