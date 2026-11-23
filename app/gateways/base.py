"""The one interface you implement to connect a payment gateway such as eGRAS.

Everything else in this project (database, API, idempotency, amount checks,
safe status transitions) stays the same whichever gateway you plug in.
"""
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal
from app.models.payment import Payment

FinalStatus = Literal["SUCCESS", "FAILED"]


@dataclass(frozen=True)
class CheckoutRedirect:
    """Where to send the citizen's browser to pay, and the form fields to post there."""
    url: str
    method: Literal["GET", "POST"] = "POST"
    fields: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class GatewayResult:
    """A payment result the gateway has vouched for (signature/checksum already verified)."""
    txn_number: str
    status: FinalStatus
    amount: Decimal
    gateway_reference: str | None = None  # e.g. the GRN / challan number eGRAS assigns


class CallbackRejected(Exception):
    """The callback could not be decrypted or verified, so it must not change any payment."""


class PaymentGateway(ABC):
    name: str = "base"
    implemented: bool = True

    @abstractmethod
    def build_checkout(self, payment: Payment) -> CheckoutRedirect:
        """Step 1: turn a stored PENDING payment into the redirect the citizen follows to pay."""

    @abstractmethod
    def parse_callback(self, data: Mapping[str, str]) -> GatewayResult:
        """Step 2: decrypt and verify what the gateway posts back. Raise CallbackRejected if untrusted."""

    async def fetch_status(self, payment: Payment) -> GatewayResult | None:
        """Step 3 (double verification): ask the gateway for the authoritative status.

        Return None when the gateway has no final answer yet.
        """
        return None
