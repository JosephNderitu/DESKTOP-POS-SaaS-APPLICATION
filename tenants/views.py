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
        plan = request.data.get('plan')

        if not business_name or not subdomain_prefix or not admin_email:
            return Response(
                {"error": "Missing required provisioning parameters."},
                status=status.HTTP_400_BAD_REQUEST
            )

        subdomain_slug = subdomain_prefix.lower().strip()
        subdomain_slug = re.sub(r"[^a-z0-9-]", "", subdomain_slug).strip("-")
        schema_name = subdomain_slug.replace("-", "_")

        if not subdomain_slug or not schema_name:
            return Response(
                {"error": "Store subdomain must contain letters or numbers."},
                status=status.HTTP_400_BAD_REQUEST
            )

        domain_name = f"{subdomain_slug}.localhost"

        try:
            # 1. Create the database tenant configuration
            tenant = Client(
                schema_name=schema_name,
                name=business_name,
                paid_until=datetime.date.today() + datetime.timedelta(days=30),
                on_trial=True
            )
            tenant.save()

            # 2. Assign the primary local loopback domain
            domain = Domain(
                domain=domain_name,
                tenant=tenant,
                is_primary=True
            )
            domain.save()

            # 3. Dynamic Schema Seeding: Swap context into the newly generated tenant
            #    and provision the Master Administrator Account.
            with tenant_context(tenant):
                # Default credentials for initial setup testing
                default_username = f"{schema_name}_admin"
                default_password = f"{schema_name}@100"

                master_user = User.objects.create_user(
                    username=default_username,
                    email=admin_email,
                    password=default_password,
                    role="MANAGER",     # Give them management rights
                    is_staff=True       # Allows them to log into http://subdomain.localhost:8000/admin/ too!
                )

            return Response({
                "success": True,
                "message": f"Database schema '{schema_name}' provisioned and seeded successfully!",
                "subdomain": subdomain_slug,
                "generated_credentials": {
                    "username": default_username,
                    "password": default_password
                }
            }, status=status.HTTP_201_CREATED)

        except IntegrityError as ie:
            print(f"[REGISTRATION ERROR] Database conflict: {ie}")
            return Response(
                {"error": "This store name or subdomain prefix is already active in our network records."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            print(f"[REGISTRATION SYSTEM CRASH] Detailed exception: {str(e)}")
            return Response(
                {"error": f"Internal automation error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
