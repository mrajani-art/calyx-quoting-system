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
    """Temporary diagnostic endpoint to check model status and test predictions."""
    import sklearn
    import joblib
    import numpy
    import os
    import traceback

    model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
    model_files = {}
    if os.path.isdir(model_dir):
        for f in sorted(os.listdir(model_dir)):
            if f.endswith(".joblib"):
                model_files[f] = os.path.getsize(os.path.join(model_dir, f))

    # Check if predictor loaded
    from api.services.prediction_service import _predictor, generate_instant_quote
    predictor_status = "loaded" if _predictor is not None else "not loaded"

    # Try loading a preprocessor
    load_test = {}
    for name in ["dazpak", "ross", "tedpack_air", "tedpack_ocean"]:
        fpath = os.path.join(model_dir, f"{name}_preprocessor.joblib")
        try:
            obj = joblib.load(fpath)
            load_test[name] = f"OK: {type(obj).__name__}"
        except Exception as e:
            load_test[name] = f"FAILED: {str(e)[:200]}"

    # Test an actual prediction end-to-end
    predict_test = {}
    try:
        from api.schemas.quote_request import InstantQuoteRequest
        test_req = InstantQuoteRequest(
            width=4.5, height=5, gusset=2,
            substrate="Metallic", finish="Matte",
            seal_type="Stand Up Pouch", fill_style="Top",
            zipper="None", tear_notch="Standard",
            hole_punch="None", corners="Straight",
            embellishment="None",
            quantities=[5000, 10000],
            lead_id="debug-test",
        )
        raw_result = generate_instant_quote(test_req)
        for method in ["digital", "flexographic", "international_air", "international_ocean"]:
            val = raw_result.get(method)
            if val is None:
                predict_test[method] = "null"
            else:
                predict_test[method] = f"OK: {len(val.tiers)} tiers"
    except Exception as e:
        predict_test["error"] = f"{type(e).__name__}: {str(e)[:300]}"
        predict_test["traceback"] = traceback.format_exc()[-500:]

    # Test each prediction individually with detailed error capture
    individual_tests = {}
    try:
        from api.services.prediction_service import get_predictor, _build_internal_specs
        predictor = get_predictor()
        specs = _build_internal_specs(test_req)
        individual_tests["specs"] = {k: str(v)[:50] for k, v in specs.items()}

        # Test digital (internal calculator)
        try:
            digital_specs = {**specs, "print_method": "Digital"}
            digital_result = predictor.predict(digital_specs, [5000])
            preds = digital_result.get("predictions", [])
            individual_tests["digital"] = {
                "vendor": digital_result.get("vendor"),
                "prediction_count": len(preds),
                "first_pred": str(preds[0])[:200] if preds else "empty",
            }
        except Exception as e:
            individual_tests["digital"] = {
                "error": f"{type(e).__name__}: {str(e)[:300]}",
                "traceback": traceback.format_exc()[-500:],
            }

        # Test flexographic (dazpak ML)
        try:
            flexo_specs = {**specs, "print_method": "Flexographic"}
            flexo_result = predictor.predict(flexo_specs, [50000])
            preds = flexo_result.get("predictions", [])
            individual_tests["flexographic"] = {
                "vendor": flexo_result.get("vendor"),
                "prediction_count": len(preds),
                "first_pred": str(preds[0])[:200] if preds else "empty",
            }
        except Exception as e:
            individual_tests["flexographic"] = {
                "error": f"{type(e).__name__}: {str(e)[:300]}",
                "traceback": traceback.format_exc()[-500:],
            }

        # Test tedpack
        try:
            tedpack_result = predictor.predict(specs, [10000], vendor_override="tedpack")
            preds = tedpack_result.get("predictions", [])
            individual_tests["tedpack"] = {
                "vendor": tedpack_result.get("vendor"),
                "prediction_count": len(preds),
                "first_pred": str(preds[0])[:200] if preds else "empty",
            }
        except Exception as e:
            individual_tests["tedpack"] = {
                "error": f"{type(e).__name__}: {str(e)[:300]}",
                "traceback": traceback.format_exc()[-500:],
            }

    except Exception as e:
        individual_tests["setup_error"] = f"{type(e).__name__}: {str(e)[:300]}"
        individual_tests["setup_traceback"] = traceback.format_exc()[-500:]

    return {
        "sklearn_version": sklearn.__version__,
        "joblib_version": joblib.__version__,
        "numpy_version": numpy.__version__,
        "model_dir": model_dir,
        "model_dir_exists": os.path.isdir(model_dir),
        "model_files": model_files,
        "predictor_status": predictor_status,
        "load_test": load_test,
        "predict_test": predict_test,
        "individual_tests": individual_tests,
    }
