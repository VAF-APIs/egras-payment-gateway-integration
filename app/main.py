"""eGRAS payment integration starter. Run: uvicorn app.main:app --reload"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api import callbacks, mock_egras, payments
from app.core.config import get_settings
from app.core.dependencies import get_store
from app.gateways import get_gateway
from app.services.payment_store import InMemoryPaymentStore

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(application: FastAPI):
    settings = get_settings()
    settings.validate_runtime()
    if not get_gateway(settings).implemented:
        raise RuntimeError("GATEWAY_MODE=egras, but app/gateways/egras.py is not completed yet. "
                           "Follow docs/EGRAS_INTEGRATION.md (or contact https://vaf.ai).")
    if settings.app_env == "production" and isinstance(get_store(), InMemoryPaymentStore):
        raise RuntimeError("Production needs a database-backed PaymentStore. See app/services/payment_store.py.")
    yield


app = FastAPI(
    title="eGRAS Payment Gateway Integration",
    version="1.0.0",
    description="Open-source starter by Visual App Foundry (https://vaf.ai) for collecting government "
                "fees through eGRAS. Runs end to end with a built-in mock gateway.",
    lifespan=lifespan,
)
app.include_router(payments.router)
app.include_router(callbacks.router)
app.include_router(mock_egras.router)


@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok"}
