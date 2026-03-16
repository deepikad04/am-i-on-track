import os
from dotenv import load_dotenv

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
NOVA_MODEL_ID = os.getenv("NOVA_MODEL_ID", "us.amazon.nova-2-lite-v1:0")
NOVA_PRO_MODEL_ID = os.getenv("NOVA_PRO_MODEL_ID", "us.amazon.nova-2-pro-v1:0")
NOVA_EMBED_MODEL_ID = os.getenv("NOVA_EMBED_MODEL_ID", "amazon.nova-2-multimodal-embeddings-v1:0")
NOVA_CANVAS_MODEL_ID = os.getenv("NOVA_CANVAS_MODEL_ID", "amazon.nova-canvas-v1:0")
# Render provides postgres:// but asyncpg needs postgresql+asyncpg://
_raw_db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://amiontrack:amiontrack@localhost:5432/amiontrack")
if _raw_db_url.startswith("postgres://"):
    _raw_db_url = _raw_db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif _raw_db_url.startswith("postgresql://"):
    _raw_db_url = _raw_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
DATABASE_URL = _raw_db_url
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
MAX_CREDITS_PER_SEMESTER = 18
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production-amiontrack-secret-key")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
BEDROCK_GUARDRAIL_ID = os.getenv("BEDROCK_GUARDRAIL_ID", "")
BEDROCK_GUARDRAIL_VERSION = os.getenv("BEDROCK_GUARDRAIL_VERSION", "DRAFT")
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() in ("true", "1", "yes")
