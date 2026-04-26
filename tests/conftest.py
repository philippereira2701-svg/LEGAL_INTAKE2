import os
import sys
from pathlib import Path


os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test_db")
os.environ.setdefault("FLASK_SECRET_KEY", "test-secret-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
