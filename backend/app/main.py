import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database.db import init_db, async_session
from app.database.seed import seed_sample_data
from app.api.routes import auth, upload, degree, simulation
from app.models.schemas import HealthResponse
from app.middleware import RequestTracingMiddleware, RateLimitMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing database...")
    await init_db()
    async with async_session() as db:
        await seed_sample_data(db)
    logger.info("Am I On Track? backend ready")
    yield
    # Shutdown
    logger.info("Shutting down...")


app = FastAPI(
    title="Am I On Track?",
    description="Agentic AI Academic Trajectory Simulator",
    version="1.0.0",
    lifespan=lifespan,
)

_default_origins = ["http://localhost:5173", "http://localhost:3000"]
_extra = os.getenv("ALLOWED_ORIGINS", "")
_origins = _default_origins + [o.strip() for o in _extra.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestTracingMiddleware)
app.add_middleware(RateLimitMiddleware, max_concurrent=5)

# Register routes
app.include_router(auth.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(degree.router, prefix="/api")
app.include_router(simulation.router, prefix="/api")


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check + Bedrock connectivity test."""
    bedrock_connected = False
    try:
        from app.services.bedrock_client import bedrock
        bedrock_connected = await bedrock.check_connection_async()
    except Exception:
        pass
    return HealthResponse(status="ok", bedrock_connected=bedrock_connected)
