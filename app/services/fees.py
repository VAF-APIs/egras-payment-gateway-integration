"""Server-side fee table. The amount is ALWAYS decided here, never sent by the browser/client.

In eGRAS every receipt is credited to a budget "head of account" assigned by the
finance department. Replace these demo rows with your department's services, amounts
and heads of account (or load them from your database).
"""
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Fee:
    service_code: str
    description: str
    amount: Decimal
    head_of_account: str


DEMO_FEES: dict[str, Fee] = {
    fee.service_code: fee for fee in (
        Fee("DEMO_CERTIFICATE", "Certificate issue fee (demo)", Decimal("50.00"), "0000-00-000-00-00"),
        Fee("DEMO_LICENSE_RENEWAL", "Licence renewal fee (demo)", Decimal("500.00"), "0000-00-000-00-01"),
    )
}


def get_fee(service_code: str) -> Fee | None:
    return DEMO_FEES.get(service_code)


def list_fees() -> list[Fee]:
    return list(DEMO_FEES.values())
