from app.core.config import Settings
from app.gateways.base import PaymentGateway


def get_gateway(settings: Settings) -> PaymentGateway:
    if settings.gateway_mode == "egras":
        from app.gateways.egras import EgrasGateway
        return EgrasGateway(settings)
    from app.gateways.mock import MockGateway
    return MockGateway(settings)
