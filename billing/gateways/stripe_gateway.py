import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_API_SECRET_KEY



class StripeGateway:
    def initiate_checkout(self, transaction, request=None):
        interval = 'year' if transaction.plan.billing_cycle == 'YEARLY' else 'month'
        session = stripe.checkout.Session.create(
            mode='subscription',
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {'name': f"RVC POS — {transaction.plan.name}"},
                    'unit_amount': int(transaction.plan.price_usd * 100),
                    'recurring': {'interval': interval},
                },
                'quantity': 1,
            }],
            success_url=f"{settings.FRONTEND_SUCCESS_URL}?txn={transaction.id}",
            cancel_url=f"{settings.FRONTEND_CANCEL_URL}?txn={transaction.id}",
            client_reference_id=str(transaction.id),
        )
        transaction.gateway_reference = session.id
        transaction.save(update_fields=['gateway_reference'])
        return {"checkout_url": session.url, "session_id": session.id}

    @staticmethod
    def handle_webhook(request):
        """Returns the transaction id from a verified checkout.session.completed
        event, or None if the signature is bad or the event isn't relevant."""
        try:
            event = stripe.Webhook.construct_event(
                request.body, request.META.get('HTTP_STRIPE_SIGNATURE'), settings.STRIPE_API_WEBHOOK_SECRET
            )
        except (ValueError, stripe.error.SignatureVerificationError):
            return None

        if event['type'] == 'checkout.session.completed':
            return event['data']['object'].get('client_reference_id')
        return None