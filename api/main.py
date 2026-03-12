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

from api.routers import leads, quotes
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
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(leads.router)
app.include_router(quotes.router)


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "calyx-quoting-api",
        "version": "1.0.0",
    }


@app.get("/api/v1/debug/models")
async def debug_models():
    """Temporary diagnostic endpoint to check model status."""
    import sklearn
    import joblib
    import numpy
    import os

    model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
    model_files = {}
    if os.path.isdir(model_dir):
        for f in sorted(os.listdir(model_dir)):
            if f.endswith(".joblib"):
                model_files[f] = os.path.getsize(os.path.join(model_dir, f))

    # Check if predictor loaded
    from api.services.prediction_service import _predictor
    predictor_status = "loaded" if _predictor is not None else "not loaded"

    # Try loading a preprocessor
    load_test = {}
    for name in ["dazpak", "ross", "tedpack_air", "internal"]:
        fpath = os.path.join(model_dir, f"{name}_preprocessor.joblib")
        try:
            obj = joblib.load(fpath)
            load_test[name] = f"OK: {type(obj).__name__}"
        except Exception as e:
            load_test[name] = f"FAILED: {str(e)[:200]}"

    return {
        "sklearn_version": sklearn.__version__,
        "joblib_version": joblib.__version__,
        "numpy_version": numpy.__version__,
        "model_dir": model_dir,
        "model_dir_exists": os.path.isdir(model_dir),
        "model_files": model_files,
        "predictor_status": predictor_status,
        "load_test": load_test,
    }
