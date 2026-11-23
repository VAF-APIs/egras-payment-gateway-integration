"""Payment rules that stay the same whichever gateway is plugged in."""
import logging
import secrets
from collections.abc import Mapping
from datetime import datetime, timezone
from fastapi import HTTPException
from app.gateways.base import CallbackRejected, GatewayResult, PaymentGateway
from app.models.payment import Payment
from app.schemas.payment import CheckoutOut, CreatePaymentRequest, CreatePaymentResponse, PaymentOut
from app.services.fees import get_fee
from app.services.payment_store import PaymentStore

logger = logging.getLogger(__name__)


def new_txn_number() -> str:
    """Alphanumeric and short, because government gateways often restrict reference formats."""
    return f"TXN{datetime.now(timezone.utc):%Y%m%d}{secrets.token_hex(6).upper()}"


class PaymentService:
    def __init__(self, store: PaymentStore, gateway: PaymentGateway):
        self.store = store
        self.gateway = gateway

    async def create(self, user_id: str, req: CreatePaymentRequest) -> CreatePaymentResponse:
        fee = get_fee(req.service_code)
        if fee is None:
            raise HTTPException(422, "Unknown service_code. GET /payments/fees lists the valid codes.")
        # Retrying with the same reference_id returns the same payment (no double charge).
        payment = await self.store.get_or_create(Payment(
            txn_number=new_txn_number(), user_id=user_id, reference_id=req.reference_id,
            service_code=fee.service_code, head_of_account=fee.head_of_account,
            payer_name=req.payer_name, amount=fee.amount,
        ))
        if payment.service_code != fee.service_code:
            raise HTTPException(409, "reference_id already used for a different service")
        checkout = None
        if payment.status == "PENDING":
            redirect = self.gateway.build_checkout(payment)
            checkout = CheckoutOut(url=redirect.url, method=redirect.method, fields=redirect.fields)
        return CreatePaymentResponse(payment=PaymentOut.model_validate(payment), checkout=checkout)

    async def handle_callback(self, data: Mapping[str, str]) -> Payment:
        try:
            result = self.gateway.parse_callback(data)
        except CallbackRejected as exc:
            logger.warning("Rejected %s callback: %s", self.gateway.name, exc)
            raise HTTPException(400, "Callback rejected") from None
        return await self._apply(result)

    async def _apply(self, result: GatewayResult) -> Payment:
        payment = await self.store.by_txn(result.txn_number)
        if payment is None:
            raise HTTPException(404, "Payment not found")
        if payment.amount != result.amount:
            logger.error("Amount mismatch on %s: expected %s, gateway says %s", payment.txn_number, payment.amount, result.amount)
            raise HTTPException(400, "Amount mismatch")
        if not await self.store.finalize(result.txn_number, result.status, result.gateway_reference):
            current = await self.store.by_txn(result.txn_number)
            if current.status != result.status:
                logger.error("Conflicting result for %s: stored %s, received %s", current.txn_number, current.status, result.status)
                raise HTTPException(409, "Payment already finalized with a different status")
            return current  # duplicate callback: safe to acknowledge again
        return await self.store.by_txn(result.txn_number)

    async def get_by_txn(self, txn_number: str) -> Payment | None:
        return await self.store.by_txn(txn_number)

    async def get_for_user(self, user_id: str, txn_number: str) -> Payment:
        payment = await self.store.by_txn(txn_number)
        if payment is None or payment.user_id != user_id:
            raise HTTPException(404, "Payment not found")
        return payment

    async def history(self, user_id: str, *, status: str | None, reference_id: str | None,
                      limit: int, offset: int) -> list[Payment]:
        return await self.store.list_for_user(user_id, status=status, reference_id=reference_id, limit=limit, offset=offset)

    async def reconcile(self, user_id: str, txn_number: str) -> Payment:
        """For payments stuck in PENDING: ask the gateway directly (double verification)."""
        payment = await self.get_for_user(user_id, txn_number)
        if payment.status != "PENDING":
            return payment
        result = await self.gateway.fetch_status(payment)
        if result is None:
            return payment
        if result.txn_number != payment.txn_number:
            raise HTTPException(502, "Gateway returned a different transaction")
        return await self._apply(result)
