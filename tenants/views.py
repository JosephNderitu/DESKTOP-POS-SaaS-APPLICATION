import datetime
import re
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.db import IntegrityError
from django_tenants.utils import tenant_context

from .models import Client, Domain
from users.models import User  # Import your custom User model

class TenantRegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        business_name = request.data.get('business_name')
        subdomain_prefix = request.data.get('subdomain')
        admin_email = request.data.get('email')
        signup_choice = (request.data.get('signup_choice') or '').upper()  # "TRIAL" or "PAID"
        plan_code = request.data.get('plan_code')

        if not business_name or not subdomain_prefix or not admin_email:
            return Response({"error": "Missing required provisioning parameters."}, status=status.HTTP_400_BAD_REQUEST)

        if signup_choice not in ('TRIAL', 'PAID'):
            return Response({"error": "Choose either a free trial or a paid plan to continue."}, status=status.HTTP_400_BAD_REQUEST)

        if signup_choice == 'TRIAL':
            # One free trial per email, ever — checked against the public
            # schema's Client table, which is why owner_email lives there
            # rather than only inside each tenant's own User table.
            if Client.objects.filter(owner_email__iexact=admin_email).exists():
                return Response(
                    {"error": "A free trial or store has already been created with this email. Choose a paid plan to continue."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        elif not plan_code:
            return Response({"error": "A plan_code is required for a paid signup."}, status=status.HTTP_400_BAD_REQUEST)

        subdomain_slug = re.sub(r"[^a-z0-9-]", "", subdomain_prefix.lower().strip()).strip("-")
        schema_name = subdomain_slug.replace("-", "_")
        if not subdomain_slug or not schema_name:
            return Response({"error": "Store subdomain must contain letters or numbers."}, status=status.HTTP_400_BAD_REQUEST)

        domain_name = f"{subdomain_slug}.localhost"

        try:
            tenant = Client(
                schema_name=schema_name,
                name=business_name,
                owner_email=admin_email,
                paid_until=datetime.date.today() + datetime.timedelta(days=30),
            )
            if signup_choice == 'TRIAL':
                tenant.on_trial = True
                tenant.subscription_status = 'TRIAL'
            else:
                tenant.on_trial = False
                tenant.subscription_status = 'PENDING_PAYMENT'
                tenant.subscription_plan = plan_code
                tenant.suspended_reason = 'Awaiting first payment.'
            tenant.save()

            Domain(domain=domain_name, tenant=tenant, is_primary=True).save()

            with tenant_context(tenant):
                default_username = f"{schema_name}_admin"
                default_password = f"{schema_name}@100"
                User.objects.create_user(
                    username=default_username, email=admin_email, password=default_password,
                    role="MANAGER", is_staff=True,
                )

            return Response({
                "success": True,
                "subdomain": subdomain_slug,
                "signup_choice": signup_choice,
                "generated_credentials": {"username": default_username, "password": default_password},
            }, status=status.HTTP_201_CREATED)

        except IntegrityError:
            return Response({"error": "This store name or subdomain prefix is already active."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Internal automation error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)