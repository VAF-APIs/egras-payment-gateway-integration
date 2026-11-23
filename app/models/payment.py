"""The payment record this integration needs. Store it in whatever database you already use."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Payment:
    txn_number: str          # our unique reference sent to eGRAS (alphanumeric)
    user_id: str             # the citizen/user who pays
    reference_id: str        # your application/order number (unique per user)
    service_code: str
    head_of_account: str     # budget head the money is credited to
    payer_name: str
    amount: Decimal
    status: str = "PENDING"  # PENDING | SUCCESS | FAILED
    gateway_reference: str | None = None  # GRN / challan number from eGRAS
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)
