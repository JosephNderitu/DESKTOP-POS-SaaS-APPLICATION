from .stripe_gateway import StripeGateway
from .paypal_gateway import PayPalGateway
from .mpesa_gateway import MpesaGateway

_GATEWAYS = {'STRIPE': StripeGateway, 'PAYPAL': PayPalGateway, 'MPESA': MpesaGateway}


def get_gateway(name):
    gateway_class = _GATEWAYS.get(name)
    if not gateway_class:
        raise ValueError(f"Unsupported payment gateway: {name}")
    return gateway_class()