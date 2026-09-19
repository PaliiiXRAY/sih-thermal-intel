import os
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv(override=False)

# Application Configuration
APP_MODE = os.environ.get("APP_MODE", "development")

# Database Configuration
DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    "postgresql+psycopg://postgres:postgres@localhost:5432/firesense"
)

# JWT Authentication Configuration
JWT_SECRET_KEY = os.environ.get(
    "JWT_SECRET_KEY", 
    "firesense-dev-secret-key-change-in-production-32bytes-min"
)
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.environ.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440")
)

# CORS Configuration
raw_cors = os.environ.get(
    "CORS_ORIGINS", 
    "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"
)
CORS_ORIGINS = [origin.strip() for origin in raw_cors.split(",") if origin.strip()]
