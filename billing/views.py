from django.shortcuts import render
from django.http import HttpResponse
from django_tenants.utils import schema_context, get_public_schema_name
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .gateways import get_gateway
from .gateways.stripe_gateway import StripeGateway
from .models import SubscriptionPlan, Transaction
from .utils import activate_subscription

import stripe
from django.conf import settings


class SubscriptionPlanListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        plans = SubscriptionPlan.objects.filter(is_active=True)
        return Response([{
            "code": p.code, "name": p.name, "tagline": p.tagline,
            "price_kes": str(p.price_kes), "price_usd": str(p.price_usd),
            "billing_cycle": p.billing_cycle, "max_terminals": p.max_terminals,
            "max_staff": p.max_staff, "features": p.features,
        } for p in plans])


class InitiateSubscriptionCheckoutView(APIView):
    """Reached via a tenant subdomain — the caller is already authenticated
    with their tenant-scoped token. Billing tables live in the public
    schema, so the actual queries are wrapped in schema_context."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role not in ('ADMIN', 'MANAGER'):
            return Response({"error": "Only store managers can manage the subscription."}, status=status.HTTP_403_FORBIDDEN)

        plan_code = request.data.get('plan_code')
        gateway_name = (request.data.get('gateway') or '').upper()
        if gateway_name not in ('STRIPE', 'PAYPAL', 'MPESA'):
            return Response({"error": "gateway must be STRIPE, PAYPAL, or MPESA."}, status=status.HTTP_400_BAD_REQUEST)

        tenant_schema = request.tenant.schema_name

        with schema_context(get_public_schema_name()):
            plan = SubscriptionPlan.objects.filter(code=plan_code, is_active=True).first()
            if not plan:
                return Response({"error": "Invalid or inactive plan."}, status=status.HTTP_404_NOT_FOUND)

            amount = plan.price_kes if gateway_name == 'MPESA' else plan.price_usd
            currency = 'KES' if gateway_name == 'MPESA' else 'USD'

            transaction = Transaction.objects.create(
                tenant_schema=tenant_schema, plan=plan, gateway=gateway_name,
                amount=amount, currency=currency, status='PENDING',
            )
            try:
                result = get_gateway(gateway_name).initiate_checkout(transaction, request)
            except Exception as e:
                transaction.status = 'FAILED'
                transaction.save(update_fields=['status'])
                return Response({"error": f"Could not start checkout: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

        result['transaction_id'] = transaction.id
        return Response(result, status=status.HTTP_202_ACCEPTED)


class StripeWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        txn_id = StripeGateway.handle_webhook(request)
        if txn_id:
            transaction = Transaction.objects.filter(id=txn_id, status='PENDING').first()
            if transaction:
                activate_subscription(transaction)
        return HttpResponse(status=200)  # Stripe expects 200 regardless, to stop retrying


class PayPalCaptureView(APIView):
    """The desktop client calls this once the user returns from PayPal's approval page."""
    permission_classes = [AllowAny]

    def post(self, request):
        order_id = request.data.get('order_id')
        transaction = Transaction.objects.filter(gateway_reference=order_id, gateway='PAYPAL', status='PENDING').first()
        if not transaction:
            return Response({"error": "Transaction not found."}, status=status.HTTP_404_NOT_FOUND)

        if get_gateway('PAYPAL').capture_order(order_id):
            activate_subscription(transaction)
            return Response({"success": True})

        transaction.status = 'FAILED'
        transaction.save(update_fields=['status'])
        return Response({"success": False}, status=status.HTTP_402_PAYMENT_REQUIRED)


class MpesaCallbackView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        stk_callback = request.data.get('Body', {}).get('stkCallback', {})
        checkout_request_id = stk_callback.get('CheckoutRequestID')
        result_code = stk_callback.get('ResultCode')

        transaction = Transaction.objects.filter(
            gateway_reference=checkout_request_id, gateway='MPESA', status='PENDING'
        ).first()
        if transaction:
            transaction.raw_payload = request.data
            if result_code == 0:
                activate_subscription(transaction)
            else:
                transaction.status = 'FAILED'
                transaction.save(update_fields=['status', 'raw_payload'])

        return Response({"ResultCode": 0, "ResultDesc": "Accepted"})
    

class StripeConfirmCheckoutView(APIView):
    """
    Called by the client immediately after Stripe redirects back to
    FRONTEND_SUCCESS_URL. Verifies payment status directly against Stripe's
    API using the secret key — no webhook, no CLI, no public URL needed.
    The webhook view stays in the codebase as a production-grade backstop
    for cases where the browser redirect never completes (closed tab,
    crashed client, etc.), but isn't required for this test.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        transaction_id = request.data.get('transaction_id')
        transaction = Transaction.objects.filter(id=transaction_id, gateway='STRIPE', status='PENDING').first()
        if not transaction:
            return Response({"error": "Transaction not found or already processed."}, status=status.HTTP_404_NOT_FOUND)

        stripe.api_key = settings.STRIPE_API_SECRET_KEY
        try:
            session = stripe.checkout.Session.retrieve(transaction.gateway_reference)
        except stripe.error.StripeError as e:
            return Response({"error": f"Could not verify payment: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

        if session.payment_status == 'paid' or session.status == 'complete':
            activate_subscription(transaction)
            return Response({"success": True, "status": "ACTIVE"})

        return Response({"success": False, "status": "not yet completed"}, status=status.HTTP_402_PAYMENT_REQUIRED)


def billing_success_page(request):
    """
    Landing page after a gateway redirects back. Doesn't finalize anything
    itself — the page's JS calls the appropriate confirm/capture endpoint,
    so this stays a plain, fast-loading page with no tenant-schema lookups.
    """
    return render(request, 'billing/success.html', {
        'transaction_id': request.GET.get('txn', ''),
        'gateway': (request.GET.get('gateway') or 'stripe').lower(),
        # PayPal's approval redirect appends its own `token` param, which
        # equals the order id we need for the capture call
        'order_id': request.GET.get('token', ''),
    })


def billing_cancel_page(request):
    return render(request, 'billing/cancel.html', {
        'transaction_id': request.GET.get('txn', ''),
    })


class MarkTransactionCancelledView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        txn_id = request.data.get('transaction_id')
        Transaction.objects.filter(id=txn_id, status='PENDING').update(status='CANCELLED')
        return Response({"success": True})
    
