import os
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv(override=False)


def _require(name: str) -> str:
    """Return a required env var, refusing to start with a known fallback value."""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} is not set. Refusing to boot with a hardcoded/default secret. "
            f"Set it in the environment or a .env file (see .env.example)."
        )
    return value


# Application Configuration
APP_MODE = os.environ.get("APP_MODE", "development")

# Database Configuration (required — no silent local fallback)
DATABASE_URL = _require("DATABASE_URL")

# JWT Authentication Configuration (required — never fall back to a shipped secret)
JWT_SECRET_KEY = _require("JWT_SECRET_KEY")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.environ.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440")
)

# CORS Configuration
raw_cors = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173",
)
CORS_ORIGINS = [origin.strip() for origin in raw_cors.split(",") if origin.strip()]