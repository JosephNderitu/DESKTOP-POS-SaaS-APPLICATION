# RVC POS — Multi-Tenant SaaS Point of Sale

A multi-tenant POS system for retail stores. Each store operates on an isolated
subdomain (`storename.yourdomain.com`) with its own schema-separated data —
products, sales, and staff accounts — while a shared public schema handles
tenant onboarding and billing.

## Stack
- **Backend:** Django, Django REST Framework, django-tenants (PostgreSQL schema-per-tenant)
- **Desktop client:** PyQt6
- **Infra:** Docker Compose, Redis, Celery, Nginx, OSRM

## Setup

1. Clone and create a virtual environment
```bash
   git clone <repo-url>
   cd pos-system-saas-app
   python -m venv venv
   venv\Scripts\activate      # Windows
   pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and fill in real values
```bash
   cp .env.example .env
```

3. Run migrations across all schemas
```bash
   python manage.py migrate_schemas
```

4. Create a platform superuser (public schema)
```bash
   python manage.py createsuperuser
```

5. Create your first tenant (store) — via the admin panel or `TenantRegistrationView`,
   then create that store's own superuser/manager account:
```bash
   python manage.py tenant_command createsuperuser --schema=<store_schema_name>
```

6. Run the backend
```bash
   python manage.py runserver
```

7. Run the desktop client
```bash
   cd desktop_clients
   python app.py
```

## Notes
- `users` is intentionally listed in both `SHARED_APPS` and `TENANT_APPS`:
  platform admins live in `public`, store staff live inside each tenant schema.
  Always use `tenant_command` when managing store-level accounts.
- Product images are auto background-removed and compressed on upload (see `inventory/image_processing.py`).