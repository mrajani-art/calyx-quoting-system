"""
FastAPI application for the Calyx Containers customer-facing quoting portal.

Provides instant quotes via ML prediction models. All responses are
sanitized to ensure no internal vendor data, costs, or model metrics
are ever exposed to customers.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import leads, quotes, files
from api.services.prediction_service import load_models

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ML models at startup, clean up on shutdown."""
    logger.info("Loading ML prediction models...")
    try:
        load_models()
        logger.info("ML models loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load ML models: {e}")
        logger.warning("API will start but quote predictions may fail")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Calyx Containers Quoting API",
    description="Instant packaging quotes for custom stand-up pouches and flat bags.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://quote.calyxcontainers.com",
        "https://calyx-quoting-portal.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(leads.router)
app.include_router(quotes.router)
app.include_router(files.router)

# Conditionally register debug router when DEBUG_API_KEY is set
import os
if os.getenv("DEBUG_API_KEY"):
    from api.routers import debug
    app.include_router(debug.router)


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "calyx-quoting-api",
        "version": "1.0.0",
    }
