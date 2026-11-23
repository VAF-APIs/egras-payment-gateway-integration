"""Department-facing API: your backend creates payments and reads their status here."""
from typing import Literal
from fastapi import APIRouter, Depends, Query
from app.core.dependencies import get_payment_service
from app.core.security import current_user, require_api_key
from app.schemas.payment import CreatePaymentRequest, CreatePaymentResponse, FeeOut, PaymentOut
from app.services.fees import list_fees
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"], dependencies=[Depends(require_api_key)])


@router.get("/fees", response_model=list[FeeOut], summary="List payable services and their server-side amounts")
async def fees():
    return list_fees()


@router.post("", response_model=CreatePaymentResponse, summary="1. Create a payment and get the checkout redirect")
async def create_payment(request: CreatePaymentRequest, user_id: str = Depends(current_user),
                         service: PaymentService = Depends(get_payment_service)):
    return await service.create(user_id, request)


@router.get("", response_model=list[PaymentOut], summary="List the user's payments")
async def payment_history(
    status: Literal["PENDING", "SUCCESS", "FAILED"] | None = None,
    reference_id: str | None = Query(default=None, max_length=120),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(current_user),
    service: PaymentService = Depends(get_payment_service),
):
    return await service.history(user_id, status=status, reference_id=reference_id, limit=limit, offset=offset)


@router.get("/{txn_number}", response_model=PaymentOut, summary="3. Read the server-side payment status")
async def payment_status(txn_number: str, user_id: str = Depends(current_user),
                         service: PaymentService = Depends(get_payment_service)):
    return await service.get_for_user(user_id, txn_number)


@router.post("/{txn_number}/reconcile", response_model=PaymentOut,
             summary="Re-check a PENDING payment directly with the gateway (double verification)")
async def reconcile_payment(txn_number: str, user_id: str = Depends(current_user),
                            service: PaymentService = Depends(get_payment_service)):
    return await service.reconcile(user_id, txn_number)
