import base64
import requests
from datetime import datetime
from django.conf import settings

MPESA_BASE = "https://sandbox.safaricom.co.ke" if settings.MPESA_ENV == "sandbox" else "https://api.safaricom.co.ke"


class MpesaGateway:
    def _get_access_token(self):
        response = requests.get(
            f"{MPESA_BASE}/oauth/v1/generate?grant_type=client_credentials",
            auth=(settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET), timeout=10,
        )
        response.raise_for_status()
        return response.json()["access_token"]

    def initiate_checkout(self, transaction, request=None):
        phone_number = request.data.get('phone_number') if request else None
        if not phone_number:
            raise ValueError("A phone number (format 2547XXXXXXXX) is required for M-Pesa payments.")

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
            "Amount": int(transaction.amount),
            "PartyA": phone_number,
            "PartyB": settings.MPESA_SHORTCODE,
            "PhoneNumber": phone_number,
            "CallBackURL": settings.MPESA_CALLBACK_URL,
            "AccountReference": f"RVCPOS-{transaction.id}",
            "TransactionDesc": f"{transaction.plan.name} subscription",
        }
        response = requests.post(
            f"{MPESA_BASE}/mpesa/stkpush/v1/processrequest", json=payload,
            headers={"Authorization": f"Bearer {access_token}"}, timeout=15,
        )
        response.raise_for_status()
        result = response.json()

        transaction.gateway_reference = result.get("CheckoutRequestID", "")
        transaction.save(update_fields=['gateway_reference'])
        return {
            "message": "STK push sent — ask the customer to check their phone and enter their M-Pesa PIN.",
            "checkout_request_id": result.get("CheckoutRequestID"),
        }