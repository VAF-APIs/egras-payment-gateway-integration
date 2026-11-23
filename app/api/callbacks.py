"""Gateway-facing endpoint: eGRAS (or the mock) posts the payment result here.

No API key here: the gateway cannot send yours. Trust comes only from the gateway
adapter decrypting and verifying the payload. Never mark a payment paid because the
browser was redirected to a "success" page.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.dependencies import get_payment_service
from app.schemas.payment import PaymentOut
from app.services.payment_service import PaymentService

router = APIRouter(tags=["eGRAS callback"])


async def read_callback_fields(request: Request) -> dict[str, str]:
    """Accept both JSON and HTML-form posts, since gateways commonly use either."""
    if request.headers.get("content-type", "").startswith("application/json"):
        try:
            body = await request.json()
        except ValueError:
            raise HTTPException(400, "Invalid JSON") from None
        if not isinstance(body, dict):
            raise HTTPException(400, "Expected a JSON object")
        return {str(key): str(value) for key, value in body.items() if value is not None}
    form = await request.form()
    return {key: value for key, value in form.items() if isinstance(value, str)}


@router.post("/egras/callback", response_model=PaymentOut, summary="2. Payment result posted back by the gateway")
async def egras_callback(request: Request, service: PaymentService = Depends(get_payment_service)):
    return await service.handle_callback(await read_callback_fields(request))
