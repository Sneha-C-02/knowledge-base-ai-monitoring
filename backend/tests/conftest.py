import os

os.environ.setdefault("DATABASE_CONNECTION_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/test_db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-12345678901234567890")
