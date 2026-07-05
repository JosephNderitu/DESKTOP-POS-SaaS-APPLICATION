import requests
from django.conf import settings

PAYPAL_BASE = "https://api-m.sandbox.paypal.com" if settings.PAYPAL_MODE == "sandbox" else "https://api-m.paypal.com"


class PayPalGateway:
    """
    Uses PayPal's Orders API (one-time capture) rather than the Subscriptions
    API. This is a deliberate simplification: Subscriptions requires
    pre-provisioning a Billing Plan on PayPal's side per plan/cycle first.
    Renewal today is a manual re-checkout each cycle, not auto-recurring —
    worth upgrading to the Subscriptions API later if that matters to you.
    """
    def _get_access_token(self):
        response = requests.post(
            f"{PAYPAL_BASE}/v1/oauth2/token",
            auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
            data={"grant_type": "client_credentials"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()["access_token"]

    def initiate_checkout(self, transaction, request=None):
        access_token = self._get_access_token()
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "reference_id": str(transaction.id),
                "amount": {"currency_code": "USD", "value": f"{transaction.plan.price_usd:.2f}"},
                "description": f"RVC POS — {transaction.plan.name} ({transaction.plan.get_billing_cycle_display()})",
            }],
            "application_context": {
                "return_url": f"{settings.FRONTEND_SUCCESS_URL}?txn={transaction.id}&gateway=paypal",
                "cancel_url": f"{settings.FRONTEND_CANCEL_URL}?txn={transaction.id}&gateway=paypal",
            },
        }
        response = requests.post(
            f"{PAYPAL_BASE}/v2/checkout/orders", json=payload,
            headers={"Authorization": f"Bearer {access_token}"}, timeout=10,
        )
        response.raise_for_status()
        order = response.json()
        approval_url = next(link["href"] for link in order["links"] if link["rel"] == "approve")

        transaction.gateway_reference = order["id"]
        transaction.save(update_fields=['gateway_reference'])
        return {"checkout_url": approval_url, "order_id": order["id"]}

    def capture_order(self, order_id):
        access_token = self._get_access_token()
        response = requests.post(
            f"{PAYPAL_BASE}/v2/checkout/orders/{order_id}/capture",
            headers={"Authorization": f"Bearer {access_token}"}, timeout=10,
        )
        response.raise_for_status()
        return response.json().get("status") == "COMPLETED"