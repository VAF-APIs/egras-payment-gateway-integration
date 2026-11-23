"""A pretend eGRAS/bank checkout page so you can click through a payment locally.

Only active when GATEWAY_MODE=mock. Delete this file once you go live if you like.
"""
from html import escape
from typing import Literal
from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse
from app.core.config import Settings, get_settings
from app.core.dependencies import get_payment_service
from app.gateways.mock import MockGateway
from app.services.payment_service import PaymentService


def require_mock_mode(settings: Settings = Depends(get_settings)) -> None:
    if settings.gateway_mode != "mock":
        raise HTTPException(404)


router = APIRouter(prefix="/mock-egras", tags=["Mock eGRAS (demo only)"], dependencies=[Depends(require_mock_mode)])


def page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        "<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'>"
        f"<title>{escape(title)}</title><style>body{{font-family:system-ui,sans-serif;max-width:32rem;margin:3rem auto;padding:0 1rem}}"
        "button{padding:.6rem 1.2rem;margin-right:.5rem;font-size:1rem}td{padding:.25rem .75rem .25rem 0}"
        ".note{color:#666;font-size:.9rem}</style></head><body>"
        f"<p class='note'>MOCK eGRAS - demo only, no real money moves</p><h1>{escape(title)}</h1>{body}</body></html>"
    )


@router.get("/checkout/{txn_number}", response_class=HTMLResponse, summary="Demo checkout page (citizen's browser)")
async def checkout_page(txn_number: str, service: PaymentService = Depends(get_payment_service)):
    payment = await service.get_by_txn(txn_number)
    if payment is None:
        raise HTTPException(404, "Payment not found")
    rows = "".join(
        f"<tr><td>{escape(label)}</td><td><b>{escape(str(value))}</b></td></tr>" for label, value in (
            ("Transaction", payment.txn_number), ("Payer", payment.payer_name),
            ("Head of account", payment.head_of_account), ("Amount (INR)", payment.amount),
        )
    )
    if payment.status != "PENDING":
        return page("Payment already completed", f"<table>{rows}</table><p>Status: <b>{escape(payment.status)}</b></p>")
    action = f"/mock-egras/checkout/{escape(payment.txn_number)}/complete"
    return page("Pay government fee", f"<table>{rows}</table><form method='post' action='{action}'>"
                "<button name='outcome' value='SUCCESS'>Pay</button>"
                "<button name='outcome' value='FAILED'>Simulate failure</button></form>")


@router.post("/checkout/{txn_number}/complete", response_class=HTMLResponse, summary="Demo: bank finishes the payment")
async def complete_checkout(txn_number: str, outcome: Literal["SUCCESS", "FAILED"] = Form(...),
                            service: PaymentService = Depends(get_payment_service)):
    payment = await service.get_by_txn(txn_number)
    if payment is None:
        raise HTTPException(404, "Payment not found")
    gateway = service.gateway
    assert isinstance(gateway, MockGateway)
    # Exactly what a real gateway does: post a signed result to the callback handler.
    payment = await service.handle_callback(gateway.signed_callback(payment.txn_number, outcome, payment.amount))
    return page(f"Payment {payment.status}", f"<p>Reference (mock GRN): <b>{escape(payment.gateway_reference or '-')}</b></p>"
                "<p class='note'>A real eGRAS would now return the citizen to your department portal, "
                "which should read the status from <code>GET /payments/{txn_number}</code>.</p>")
