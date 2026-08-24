import os
import sys

from src.knowledge_base_backend.bootstrap.application_factory import create_application

# Ensure the src directory is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = create_application()
