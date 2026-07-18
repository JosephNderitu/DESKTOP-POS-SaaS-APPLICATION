from django.shortcuts import render
from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

# Create your views here.
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework import status
from tenants.models import log_login_event

from .models import User

class POSLoginView(ObtainAuthToken):
    permission_classes = [AllowAny]  # Allow anyone to attempt a login request

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        tenant = request.tenant
        log_login_event(tenant, user)
        
        return Response({
            'token': token.key,
            'user_id': user.id,
            'username': user.username,
            'role': user.role,
            "subscription_status": tenant.subscription_status,
            "subscription_plan": tenant.subscription_plan,
            "trial_days_left": tenant.days_left_in_trial,
            'facial_embedding': user.facial_embedding,  # Passed to PyQt for local matching
        })
        
class PasswordResetRequestView(APIView):
    """
    Scoped entirely to the CURRENT tenant. request.tenant is already resolved
    by TenantMainMiddleware from the Host header before this view runs, and
    User.objects here only ever queries THIS schema's table — so even though
    the same email may exist as a completely separate account in another
    store's schema, this endpoint has no way to see or touch that account.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get('email') or '').strip()
        if not email:
            return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email__iexact=email).first()

        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = PasswordResetTokenGenerator().make_token(user)
            reset_link = f"http://{request.get_host()}/password-reset/confirm/?uid={uid}&token={token}"

            html_body = render_to_string('emails/password_reset.html', {
                'username': user.username,
                'store_name': request.tenant.name,
                'reset_link': reset_link,
            })
            message = EmailMultiAlternatives(
                subject="Reset your RVC POS password",
                body=f"Reset your password using this link: {reset_link}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )
            message.attach_alternative(html_body, "text/html")
            message.send(fail_silently=True)

        # Same response whether or not a match was found — prevents this
        # endpoint from being used to enumerate which emails have accounts.
        return Response({"message": "If an account with that email exists in this store, a reset link has been sent."})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        uidb64 = request.data.get('uid')
        token = request.data.get('token')
        new_password = request.data.get('new_password')

        if not uidb64 or not token or not new_password:
            return Response({"error": "uid, token, and new_password are required."}, status=status.HTTP_400_BAD_REQUEST)
        if len(new_password) < 8:
            return Response({"error": "Password must be at least 8 characters."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            return Response({"error": "This reset link is invalid or has expired."}, status=status.HTTP_400_BAD_REQUEST)

        if not PasswordResetTokenGenerator().check_token(user, token):
            return Response({"error": "This reset link is invalid or has expired."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()

        html_body = render_to_string('emails/password_changed.html', {
            'username': user.username,
            'store_name': request.tenant.name,
        })
        message = EmailMultiAlternatives(
            subject="Your RVC POS password was changed",
            body="Your password was just changed. If this wasn't you, contact support immediately.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        message.attach_alternative(html_body, "text/html")
        message.send(fail_silently=True)

        return Response({"message": "Password has been reset successfully. You can now log in."})


def password_reset_confirm_page(request):
    """The web page the emailed link opens — collects the new password and
    submits it to PasswordResetConfirmView via JS."""
    return render(request, 'password_reset_confirm.html', {
        'uid': request.GET.get('uid', ''),
        'token': request.GET.get('token', ''),
        'store_name': getattr(request.tenant, 'name', 'your store'),
    })