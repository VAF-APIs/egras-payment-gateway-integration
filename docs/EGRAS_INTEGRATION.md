# eGRAS go-live guide

This guide is for a developer who has the starter running in mock mode and now needs to connect a
real state eGRAS. Expect most of the time to go on paperwork and UAT. Thanks to the mock, the code
change is small.

> Stuck at any step? Visual App Foundry has done this before and can help: **[vaf.ai](https://vaf.ai)**

## Step 1: Get onboarded (non-technical, start this first)

Your **department** (not the software vendor) normally applies to the state finance department /
treasury, or the team that runs eGRAS, to become an integrated department. Ask for:

| Item | Where it goes |
|---|---|
| Official integration / API document (current version) | Your reference for Step 3 |
| Merchant / department code | `EGRAS_MERCHANT_CODE` |
| Encryption / checksum key(s) | `EGRAS_SECRET_KEY` (secret manager in production) |
| UAT and production payment URLs | `EGRAS_PAYMENT_URL` |
| Verification (double-verification) service URL | `EGRAS_VERIFICATION_URL` |
| Heads of account for each fee you collect | [app/services/fees.py](../app/services/fees.py) |
| Registration of your return/callback URL and server IPs | Give them `https://<your-domain>/egras/callback` |
| Test bank / test payment instructions for UAT | Testing in Step 6 |

Keep the document and keys **out of Git**. They are usually confidential.

## Step 2: Put in your real fees

Edit [app/services/fees.py](../app/services/fees.py) (or load from your database). Each payable service needs:
`service_code` (your name for it), `amount`, and the `head_of_account` the treasury assigned.
The client never sends the amount.

## Step 3: Complete the adapter

Open [app/gateways/egras.py](../app/gateways/egras.py). It has exactly four TODOs:

| TODO | Method | What to do from the document |
|---|---|---|
| 1 | `build_checkout` | Build the request fields from the stored payment: merchant code, your `txn_number`, amount, head of account, payer name, return URL. |
| 2 | `build_checkout` | Encrypt or checksum the request exactly as specified, and return the URL and form fields. |
| 3 | `parse_callback` | Decrypt the response, verify the checksum/signature and merchant code, and map status codes to `SUCCESS` / `FAILED`. Raise `CallbackRejected` on any doubt. |
| 4 | `fetch_status` | Call the verification service server to server (use `httpx` with a timeout), verify it the same way, and return the result or `None`. |

Then set `implemented = True`.

Tips:
- Put the crypto in small pure functions and unit test them against the **sample values in the
  document**. That is the fastest way to catch padding/encoding mistakes.
- Match field order, case, date format and amount format (`125.00` vs `125`) exactly. Most checksum
  failures come from formatting.
- If eGRAS posts the result to the citizen's browser (a form auto-submit) rather than server to server,
  the same `/egras/callback` works, because it accepts form posts. Still always confirm with `fetch_status`
  before issuing anything valuable.
- If eGRAS expects a specific acknowledgement body from your callback, adjust
  [app/api/callbacks.py](../app/api/callbacks.py).

You should not need to touch the payment service or API code.

## Step 4: Connect your database

Implement `PaymentStore` from [app/services/payment_store.py](../app/services/payment_store.py) on your
own database and return it from `get_store()` in [app/core/dependencies.py](../app/core/dependencies.py).
Keep the unique `(user_id, reference_id)` constraint and the single conditional `PENDING → final`
update described in that file. The in-memory demo store is refused in production.

## Step 5: Configure

```env
APP_ENV=production            # use development while in UAT
GATEWAY_MODE=egras
APP_BASE_URL=https://<your-domain>
EGRAS_PAYMENT_URL=https://...
EGRAS_VERIFICATION_URL=https://...
EGRAS_MERCHANT_CODE=...
EGRAS_SECRET_KEY=...
```

The app refuses to start if a required value is missing, a URL is not HTTPS, or the adapter is still unfinished.

## Step 6: UAT checklist

- [ ] Successful payment → status `SUCCESS`, GRN stored in `gateway_reference`
- [ ] Failed / cancelled payment → status `FAILED`
- [ ] Citizen closes the browser mid-payment → payment stays `PENDING`, and `reconcile` resolves it
- [ ] Same callback delivered twice → accepted once, no double processing
- [ ] Tampered callback (changed amount or byte) → rejected with 400
- [ ] Same `reference_id` submitted twice → one payment only
- [ ] Amounts with paise (e.g. `10.50`) round-trip exactly
- [ ] Timeouts from the verification service are handled and logged

## Step 7: Production hardening

- Replace the demo `X-User-ID` header with your portal's verified identity (JWT/OIDC).
- Run behind HTTPS with rate limits, and keep keys in a secret manager.
- Back up your payments table. It is your financial record of what eGRAS confirmed.
- Schedule a job that runs `reconcile` for payments that have been `PENDING` for more than N minutes.
- Reconcile daily against the treasury's statement/scroll if your state provides one.
- Log every callback (without secrets or personal data) for audit.

---

Prefer to hand it over? **[Visual App Foundry](https://vaf.ai)** delivers complete eGRAS integrations,
from onboarding paperwork through UAT to production support.
