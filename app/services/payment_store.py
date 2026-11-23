"""Where payments are kept. Swap the in-memory demo store for your own database.

This project deliberately ships no database code. Implement PaymentStore on top of
your existing database (PostgreSQL, MySQL, Oracle, ...) and keep the two rules below.
They are what make an eGRAS integration safe:

1. get_or_create must be atomic per (user_id, reference_id), e.g. a UNIQUE constraint,
   so a retried request can never create a second payment (double charge).
2. finalize must be a single conditional update, e.g.
       UPDATE payments SET status=?, gateway_reference=?, updated_at=now()
       WHERE txn_number=? AND status='PENDING'
   and report whether a row changed, so two callbacks can never both win.
"""
import asyncio
from dataclasses import replace
from typing import Protocol
from app.models.payment import Payment, utcnow


class PaymentStore(Protocol):
    async def get_or_create(self, payment: Payment) -> Payment:
        """Return the existing payment for (user_id, reference_id), or save and return this one."""

    async def by_txn(self, txn_number: str) -> Payment | None: ...

    async def list_for_user(self, user_id: str, *, status: str | None, reference_id: str | None,
                            limit: int, offset: int) -> list[Payment]: ...

    async def finalize(self, txn_number: str, status: str, gateway_reference: str | None) -> bool:
        """Move PENDING -> SUCCESS/FAILED atomically. False if it was not PENDING."""


class InMemoryPaymentStore:
    """Demo only: single process, lost on restart. The app refuses to use it in production."""

    def __init__(self) -> None:
        self._payments: dict[str, Payment] = {}
        self._by_reference: dict[tuple[str, str], str] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(self, payment: Payment) -> Payment:
        async with self._lock:
            key = (payment.user_id, payment.reference_id)
            if key in self._by_reference:
                return replace(self._payments[self._by_reference[key]])
            self._payments[payment.txn_number] = replace(payment)
            self._by_reference[key] = payment.txn_number
            return replace(payment)

    async def by_txn(self, txn_number: str) -> Payment | None:
        payment = self._payments.get(txn_number)
        return replace(payment) if payment else None

    async def list_for_user(self, user_id: str, *, status: str | None, reference_id: str | None,
                            limit: int, offset: int) -> list[Payment]:
        rows = [p for p in reversed(self._payments.values())  # newest first
                if p.user_id == user_id
                and (status is None or p.status == status)
                and (reference_id is None or p.reference_id == reference_id)]
        return [replace(p) for p in rows[offset:offset + limit]]

    async def finalize(self, txn_number: str, status: str, gateway_reference: str | None) -> bool:
        async with self._lock:
            payment = self._payments.get(txn_number)
            if payment is None or payment.status != "PENDING":
                return False
            payment.status, payment.gateway_reference, payment.updated_at = status, gateway_reference, utcnow()
            return True
