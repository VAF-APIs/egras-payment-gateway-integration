"""End-to-end tests against the mock gateway and the in-memory payment store."""
import uuid
import pytest
from fastapi.testclient import TestClient

API_KEY = "test-api-key-0123456789abcdefghijklmnop"
CALLBACK_SECRET = "test-callback-secret-0123456789abcdefgh"


def clear_caches():
    from app.core.config import get_settings
    from app.core.dependencies import get_store
    get_settings.cache_clear()
    get_store.cache_clear()


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("GATEWAY_MODE", "mock")
    monkeypatch.setenv("API_KEY", API_KEY)
    monkeypatch.setenv("MOCK_CALLBACK_SECRET", CALLBACK_SECRET)
    clear_caches()
    yield monkeypatch
    clear_caches()


@pytest.fixture
def client(env):
    from app.main import app
    with TestClient(app) as test_client:
        yield test_client


def user_headers(user_id: str | None = None) -> dict:
    return {"X-API-Key": API_KEY, "X-User-ID": user_id or str(uuid.uuid4())}


def create(client, headers, reference_id=None, service_code="DEMO_CERTIFICATE"):
    response = client.post("/payments", headers=headers, json={
        "reference_id": reference_id or f"APP-{uuid.uuid4().hex[:10]}",
        "service_code": service_code, "payer_name": "Demo Citizen",
    })
    return response


def signed(txn, status, amount):
    from app.core.config import get_settings
    from app.gateways.mock import MockGateway
    return MockGateway(get_settings()).signed_callback(txn, status, amount)


def test_full_mock_flow(client):
    headers = user_headers()
    assert client.get("/payments/fees", headers=headers).status_code == 200
    created = create(client, headers)
    assert created.status_code == 200, created.text
    body = created.json()
    txn = body["payment"]["txn_number"]
    assert body["payment"]["amount"] == "50.00" and body["payment"]["status"] == "PENDING"
    assert body["checkout"]["url"].endswith(f"/mock-egras/checkout/{txn}")

    checkout = client.get(f"/mock-egras/checkout/{txn}")
    assert checkout.status_code == 200 and "50.00" in checkout.text
    paid = client.post(f"/mock-egras/checkout/{txn}/complete", data={"outcome": "SUCCESS"})
    assert paid.status_code == 200 and "SUCCESS" in paid.text

    status = client.get(f"/payments/{txn}", headers=headers).json()
    assert status["status"] == "SUCCESS"
    assert status["gateway_reference"].startswith("MOCKGRN")


def test_same_reference_is_idempotent(client):
    headers = user_headers()
    first = create(client, headers, reference_id="APP-1").json()
    second = create(client, headers, reference_id="APP-1").json()
    assert first["payment"]["txn_number"] == second["payment"]["txn_number"]
    assert create(client, headers, reference_id="APP-1", service_code="DEMO_LICENSE_RENEWAL").status_code == 409


def test_unknown_service_and_auth(client):
    assert create(client, user_headers(), service_code="NOPE").status_code == 422
    assert client.get("/payments/fees").status_code == 401
    assert client.get("/payments", headers={"X-API-Key": API_KEY, "X-User-ID": "not-a-uuid"}).status_code == 401


def test_other_user_cannot_read_payment(client):
    txn = create(client, user_headers()).json()["payment"]["txn_number"]
    assert client.get(f"/payments/{txn}", headers=user_headers()).status_code == 404


def test_callback_rejects_bad_signature_and_wrong_amount(client):
    headers = user_headers()
    txn = create(client, headers).json()["payment"]["txn_number"]
    forged = signed(txn, "SUCCESS", 50) | {"signature": "0" * 64}
    assert client.post("/egras/callback", data=forged).status_code == 400
    underpaid = signed(txn, "SUCCESS", 1)
    assert client.post("/egras/callback", json=underpaid).status_code == 400
    assert client.get(f"/payments/{txn}", headers=headers).json()["status"] == "PENDING"


def test_duplicate_callback_ok_conflicting_callback_rejected(client):
    txn = create(client, user_headers()).json()["payment"]["txn_number"]
    success = signed(txn, "SUCCESS", 50)
    assert client.post("/egras/callback", data=success).status_code == 200
    assert client.post("/egras/callback", data=success).status_code == 200
    assert client.post("/egras/callback", data=signed(txn, "FAILED", 50)).status_code == 409


def test_history_filters_are_applied_before_pagination(client):
    headers = user_headers()
    for i in range(25):
        create(client, headers, reference_id=f"APP-{i:03d}")
    found = client.get("/payments", headers=headers, params={"reference_id": "APP-000"}).json()
    assert [p["reference_id"] for p in found] == ["APP-000"]
    assert client.get("/payments", headers=headers, params={"status": "SUCCESS"}).json() == []


def test_egras_mode_refuses_to_start_until_adapter_is_written(env):
    for name in ("EGRAS_PAYMENT_URL", "EGRAS_VERIFICATION_URL"):
        env.setenv(name, "https://egras.example.invalid/endpoint")
    env.setenv("EGRAS_MERCHANT_CODE", "DEMO")
    env.setenv("EGRAS_SECRET_KEY", "demo-secret")
    env.setenv("GATEWAY_MODE", "egras")
    clear_caches()
    from app.main import app
    with pytest.raises(RuntimeError, match="egras.py"):
        with TestClient(app):
            pass


def test_production_rejects_mock_gateway():
    from app.core.config import Settings
    settings = Settings(_env_file=None, app_env="production", api_key="x" * 40, mock_callback_secret="y" * 40)
    with pytest.raises(ValueError, match="mock"):
        settings.validate_runtime()
