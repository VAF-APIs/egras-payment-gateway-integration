"""eGRAS adapter skeleton. This is the only file you should need to change to go live.

eGRAS request fields, encryption/checksum algorithm, URLs, status codes and callback
format differ between states and versions. They are given to your department in the
official integration document (with UAT credentials) by the state treasury / eGRAS team.
This file deliberately does not guess them. Complete the four TODOs from that document,
test in UAT, then set `implemented = True`.

See docs/EGRAS_INTEGRATION.md for the full walkthrough.
Need help? Visual App Foundry builds and supports these integrations: https://vaf.ai
"""
from collections.abc import Mapping
from app.core.config import Settings
from app.gateways.base import CallbackRejected, CheckoutRedirect, GatewayResult, PaymentGateway
from app.models.payment import Payment

NOT_DONE = "eGRAS adapter not implemented yet. See docs/EGRAS_INTEGRATION.md"


class EgrasGateway(PaymentGateway):
    name = "egras"
    implemented = False  # The app refuses to start in GATEWAY_MODE=egras until this is True.

    def __init__(self, settings: Settings):
        self.settings = settings

    def build_checkout(self, payment: Payment) -> CheckoutRedirect:
        # TODO 1 - Build the payment request from the stored payment, never from client input.
        #   Typically: your merchant/department code (settings.egras_merchant_code),
        #   payment.txn_number as your unique reference, payment.amount,
        #   payment.head_of_account (budget head), payment.payer_name, and the return URL
        #   registered with eGRAS (e.g. f"{settings.app_base_url}/egras/callback").
        #
        # TODO 2 - Encrypt and/or checksum the request exactly as the document specifies,
        #   using settings.egras_secret_key, then return the auto-submit form target:
        #     return CheckoutRedirect(url=self.settings.egras_payment_url, method="POST",
        #                             fields={"<field name from document>": "<encrypted value>"})
        raise NotImplementedError(NOT_DONE)

    def parse_callback(self, data: Mapping[str, str]) -> GatewayResult:
        # TODO 3 - Decrypt the posted response, verify its checksum/signature with
        #   settings.egras_secret_key, and check it was issued for your merchant code.
        #   Raise CallbackRejected on ANY failure. Map eGRAS status codes to
        #   "SUCCESS" / "FAILED"; leave "pending" style codes to fetch_status (raise CallbackRejected).
        #     return GatewayResult(txn_number=..., status="SUCCESS", amount=Decimal(...),
        #                          gateway_reference=<GRN / challan number>)
        raise CallbackRejected(NOT_DONE)

    async def fetch_status(self, payment: Payment) -> GatewayResult | None:
        # TODO 4 - Double verification: call the eGRAS verification service
        #   (settings.egras_verification_url) server-to-server with httpx, verify the
        #   response the same way as TODO 3, and return the result, or None if still pending.
        #   Use this for payments whose callback never arrived (citizen closed the browser).
        raise NotImplementedError(NOT_DONE)
