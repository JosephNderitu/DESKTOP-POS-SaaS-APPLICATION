from django.shortcuts import render
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .gateways import SaleMpesaGateway, SaleStripeGateway
from .models import Payment, Sale
from .utils import CheckoutError, build_sale_from_cart, finalize_sale


class SalesCheckoutView(APIView):
    """
    POST /api/v1/sales/checkout/
    body: {
        "items": [{"product_id": "...", "quantity": 2}, ...],
        "payment_method": "CASH" | "MPESA" | "STRIPE",
        "phone_number": "2547XXXXXXXX"   (required only for MPESA)
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        payment_method = (request.data.get('payment_method') or '').upper()
        if payment_method not in ('CASH', 'MPESA', 'STRIPE'):
            return Response({"error": "payment_method must be CASH, MPESA, or STRIPE."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            sale = build_sale_from_cart(request.data.get('items', []), request.user)
        except CheckoutError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if payment_method == 'CASH':
            # Cash is handed over at the point of sale — nothing to wait on.
            finalize_sale(sale)
            Payment.objects.create(sale=sale, method='CASH', amount=sale.total_amount)
            return Response({
                "sale_id": str(sale.id), "status": "COMPLETED", "total_amount": str(sale.total_amount),
            }, status=status.HTTP_201_CREATED)

        if payment_method == 'STRIPE':
            success_url = f"http://{request.get_host()}/sales/payment/success/?sale={sale.id}"
            cancel_url = f"http://{request.get_host()}/sales/payment/cancel/?sale={sale.id}"
            try:
                session = SaleStripeGateway().create_checkout_session(sale, success_url, cancel_url)
            except Exception as e:
                return Response({"error": f"Could not start card checkout: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

            Payment.objects.create(sale=sale, method='STRIPE', amount=sale.total_amount, transaction_reference=session.id)
            return Response({
                "sale_id": str(sale.id), "status": "PENDING",
                "checkout_url": session.url, "total_amount": str(sale.total_amount),
            }, status=status.HTTP_202_ACCEPTED)

        # MPESA
        phone_number = request.data.get('phone_number')
        if not phone_number:
            return Response({"error": "phone_number is required for M-Pesa payments."}, status=status.HTTP_400_BAD_REQUEST)

        callback_url = f"http://{request.get_host()}/api/v1/sales/webhooks/mpesa/"
        try:
            result = SaleMpesaGateway().initiate_stk_push(sale, phone_number, callback_url)
        except Exception as e:
            return Response({"error": f"Could not start M-Pesa payment: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

        Payment.objects.create(
            sale=sale, method='MPESA', amount=sale.total_amount,
            transaction_reference=result.get('CheckoutRequestID', ''),
        )
        return Response({
            "sale_id": str(sale.id), "status": "PENDING",
            "message": "STK push sent. Ask the customer to enter their M-Pesa PIN.",
            "total_amount": str(sale.total_amount),
        }, status=status.HTTP_202_ACCEPTED)


class SaleStatusView(APIView):
    """GET /api/v1/sales/<sale_id>/status/ — lets the desktop client poll
    whether a pending Stripe/M-Pesa sale has completed yet."""
    permission_classes = [IsAuthenticated]

    def get(self, request, sale_id):
        sale = Sale.objects.filter(pk=sale_id).first()
        if not sale:
            return Response({"error": "Sale not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"status": sale.status, "total_amount": str(sale.total_amount)})


class SaleStripeConfirmView(APIView):
    """
    POST /api/v1/sales/<sale_id>/confirm-stripe/
    Manual confirmation path (mirrors the billing app's approach) — verifies
    directly against Stripe's API rather than requiring the Stripe CLI or
    webhook forwarding for local testing. AllowAny is intentional here: the
    sale's redirect-landing page calls this from a plain browser tab with no
    auth token, and a random UUID sale id that must also still be PENDING is
    an acceptable bar for this specific confirm-only action — same posture
    already used for the billing app's equivalent endpoint.
    """
    permission_classes = [AllowAny]

    def post(self, request, sale_id):
        sale = Sale.objects.filter(pk=sale_id, status='PENDING').first()
        if not sale:
            return Response({"error": "Sale not found or already finalized."}, status=status.HTTP_404_NOT_FOUND)

        payment = sale.payments.filter(method='STRIPE').first()
        if not payment or not payment.transaction_reference:
            return Response({"error": "No Stripe session found for this sale."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = SaleStripeGateway().retrieve_session(payment.transaction_reference)
        except Exception as e:
            return Response({"error": f"Could not verify payment: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

        if session.payment_status == 'paid' or session.status == 'complete':
            try:
                finalize_sale(sale)
            except CheckoutError as e:
                return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
            payment.gateway_response = session.to_dict()
            payment.save(update_fields=['gateway_response'])
            return Response({"status": "COMPLETED", "total_amount": str(sale.total_amount)})

        return Response({"status": "PENDING"}, status=status.HTTP_402_PAYMENT_REQUIRED)


class SaleMpesaCallbackView(APIView):
    """Safaricom Daraja calls this once the customer enters their PIN (or
    cancels/times out). No auth — Safaricom can't send our token."""
    permission_classes = [AllowAny]

    def post(self, request):
        stk_callback = request.data.get('Body', {}).get('stkCallback', {})
        checkout_request_id = stk_callback.get('CheckoutRequestID')
        result_code = stk_callback.get('ResultCode')

        payment = Payment.objects.filter(method='MPESA', transaction_reference=checkout_request_id).first()
        if payment:
            payment.gateway_response = request.data
            payment.save(update_fields=['gateway_response'])

            if result_code == 0:
                try:
                    finalize_sale(payment.sale)
                except CheckoutError:
                    pass  # stock conflict — sale stays PENDING for manual review
            else:
                payment.sale.status = 'CANCELLED'
                payment.sale.save(update_fields=['status'])

        return Response({"ResultCode": 0, "ResultDesc": "Accepted"})


def sale_payment_success_page(request):
    return render(request, 'sales/payment_success.html', {'sale_id': request.GET.get('sale', '')})


def sale_payment_cancel_page(request):
    return render(request, 'sales/payment_cancel.html', {'sale_id': request.GET.get('sale', '')})

class SaleMarkCancelledView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, sale_id):
        Sale.objects.filter(pk=sale_id, status='PENDING').update(status='CANCELLED')
        return Response({"success": True})
    
