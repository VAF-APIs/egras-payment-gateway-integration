"""Request and response shapes (these also drive the Swagger docs at /docs)."""
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class CreatePaymentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reference_id: str = Field(
        min_length=1, max_length=120, pattern=r"^[A-Za-z0-9._/-]+$", examples=["APP-2026-000123"],
        description="Your application/order number. Sending the same value again returns the same payment.",
    )
    service_code: str = Field(
        min_length=1, max_length=60, examples=["DEMO_CERTIFICATE"],
        description="Which fee to charge. The amount is looked up on the server; see GET /payments/fees.",
    )
    payer_name: str = Field(min_length=1, max_length=120, examples=["Demo Citizen"])


class FeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    service_code: str
    description: str
    amount: Decimal
    head_of_account: str


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    txn_number: str
    reference_id: str
    service_code: str
    head_of_account: str
    payer_name: str
    amount: Decimal
    status: str
    gateway_reference: str | None
    created_at: datetime
    updated_at: datetime


class CheckoutOut(BaseModel):
    url: str
    method: str
    fields: dict[str, str]


class CreatePaymentResponse(BaseModel):
    payment: PaymentOut
    checkout: CheckoutOut | None = Field(
        description="Send the citizen's browser here to pay. Null when the payment is already final.",
    )
