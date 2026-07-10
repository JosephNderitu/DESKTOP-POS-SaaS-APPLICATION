"""
One-time payment gateways for in-person POS checkout — distinct from
billing/gateways/, which handles recurring subscription billing. A sale is
mode='payment' (Stripe) / a single STK push (M-Pesa), never recurring.
"""
import base64
from datetime import datetime

import requests
import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_API_SECRET_KEY

_MPESA_BASE = "https://sandbox.safaricom.co.ke" if settings.MPESA_ENV == "sandbox" else "https://api.safaricom.co.ke"


class SaleStripeGateway:
    def create_checkout_session(self, sale, success_url, cancel_url):
        session = stripe.checkout.Session.create(
            mode='payment',
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'kes',
                    'product_data': {'name': f"POS Sale #{sale.id}"},
                    'unit_amount': int(sale.total_amount * 100),
                },
                'quantity': 1,
            }],
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=str(sale.id),
        )
        return session

    def retrieve_session(self, session_id):
        return stripe.checkout.Session.retrieve(session_id)


class SaleMpesaGateway:
    def _get_access_token(self):
        response = requests.get(
            f"{_MPESA_BASE}/oauth/v1/generate?grant_type=client_credentials",
            auth=(settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()["access_token"]

    def initiate_stk_push(self, sale, phone_number, callback_url):
        access_token = self._get_access_token()
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password = base64.b64encode(
            f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}".encode()
        ).decode()

        payload = {
            "BusinessShortCode": settings.MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(sale.total_amount),
            "PartyA": phone_number,
            "PartyB": settings.MPESA_SHORTCODE,
            "PhoneNumber": phone_number,
            "CallBackURL": callback_url,
            "AccountReference": f"SALE-{sale.id}",
            "TransactionDesc": f"POS Sale #{sale.id}",
        }
        response = requests.post(
            f"{_MPESA_BASE}/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
        response.raise_for_status()
        return response.json()