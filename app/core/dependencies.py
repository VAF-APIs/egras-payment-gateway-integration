from functools import lru_cache
from fastapi import Depends
from app.core.config import Settings, get_settings
from app.gateways import get_gateway
from app.services.payment_service import PaymentService
from app.services.payment_store import InMemoryPaymentStore, PaymentStore


@lru_cache
def get_store() -> PaymentStore:
    # Replace with your own database-backed PaymentStore (see app/services/payment_store.py).
    return InMemoryPaymentStore()


def get_payment_service(settings: Settings = Depends(get_settings)) -> PaymentService:
    return PaymentService(get_store(), get_gateway(settings))
