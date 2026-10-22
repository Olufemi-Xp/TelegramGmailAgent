import sys
import os

# Ensure project root is in sys.path for serverless resolution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
