"""A local stand-in for eGRAS so the whole flow runs without any government credentials.

It behaves like a real gateway at the boundary: it sends the citizen to a checkout
page, and the result comes back as a signed callback that is verified before use.
The signing scheme here (HMAC-SHA256) is invented for the demo. It is NOT the eGRAS format.
"""
import hashlib
import hmac
import secrets
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from app.core.config import Settings
from app.gateways.base import CallbackRejected, CheckoutRedirect, GatewayResult, PaymentGateway
from app.models.payment import Payment


def sign(secret: str, txn_number: str, status: str, amount: str, gateway_reference: str) -> str:
    canonical = f"{txn_number}|{status}|{amount}|{gateway_reference}"
    return hmac.new(secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()


class MockGateway(PaymentGateway):
    name = "mock"

    def __init__(self, settings: Settings):
        self.settings = settings

    def build_checkout(self, payment: Payment) -> CheckoutRedirect:
        base = self.settings.app_base_url.rstrip("/")
        return CheckoutRedirect(url=f"{base}/mock-egras/checkout/{payment.txn_number}", method="GET")

    def signed_callback(self, txn_number: str, status: str, amount: Decimal) -> dict[str, str]:
        """What the mock 'bank' posts back after the citizen pays (used by the demo checkout page)."""
        reference = "MOCKGRN" + secrets.token_hex(6).upper()
        amount_text = f"{amount:.2f}"
        return {
            "txn_number": txn_number, "status": status, "amount": amount_text, "gateway_reference": reference,
            "signature": sign(self.settings.mock_callback_secret, txn_number, status, amount_text, reference),
        }

    def parse_callback(self, data: Mapping[str, str]) -> GatewayResult:
        try:
            txn_number = data["txn_number"]
            status = data["status"].upper()
            amount_text = data["amount"]
            amount = Decimal(amount_text)
            reference = data.get("gateway_reference", "")
            signature = data["signature"]
        except (KeyError, AttributeError, InvalidOperation):
            raise CallbackRejected("Malformed callback") from None
        if status not in ("SUCCESS", "FAILED") or not amount.is_finite():
            raise CallbackRejected("Unsupported status or amount")
        expected = sign(self.settings.mock_callback_secret, txn_number, status, amount_text, reference)
        if not hmac.compare_digest(expected, signature):
            raise CallbackRejected("Invalid signature")
        return GatewayResult(txn_number=txn_number, status=status, amount=amount, gateway_reference=reference or None)
