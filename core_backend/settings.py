from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / '.env')

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

SECRET_KEY = env('DJANGO_SECRET_KEY')
DEBUG = env.bool('DJANGO_DEBUG', default=False)

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '.localhost', '*']

# Application definition

# Apps that manage tenant onboarding, subscription billing, and multi-domain routing
SHARED_APPS = [
    'django_tenants',  # Must be placed at the very top
    'tenants',         # Our custom tenant onboarding app
    'billing',        # Our custom subscription billing app

    # Core Django apps needed globally
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'users',          # Custom user model with roles and biometric data
]

# Apps whose tables will be isolated within each individual tenant's store schema
TENANT_APPS = [
    'django.contrib.admin',  # Keep tenant admin history beside tenant users
    'django.contrib.auth',  # Cashiers/Managers are isolated inside their specific store
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Our feature modules
    'rest_framework.authtoken',
    'inventory',  # Products separate per store
    'sales',      # Receipts separate per store
    'users',      # Custom user roles per store
]

# Combined application list required by Django's execution engine
INSTALLED_APPS = []
for app in SHARED_APPS + TENANT_APPS:
    if app not in INSTALLED_APPS:
        INSTALLED_APPS.append(app)

MIDDLEWARE = [
    'django_tenants.middleware.main.TenantMainMiddleware',  # MUST BE FIRST
    'tenants.middleware.TenantAccessControlMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',           # Excellent for static assets
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core_backend.tenant_urls'
PUBLIC_SCHEMA_URLCONF = 'core_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core_backend.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

# core_backend/settings.py

DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST', default='127.0.0.1'),
        'PORT': env('DB_PORT', default='5432'),
    }
}

# Tell Django how to route queries across multiple schemas
DATABASE_ROUTERS = (
    'django_tenants.routers.TenantSyncRouter',
)

# Define which models represent the Tenant and its Domain routing maps
TENANT_MODEL = 'tenants.Client'  # We will build this model next
TENANT_DOMAIN_MODEL = 'tenants.Domain'  # We will build this model next


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTH_USER_MODEL = 'users.User'

# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'  # Add this line
STATICFILES_DIRS = [
    BASE_DIR / 'static',  # Add this line if you have a static folder
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Force Django to use the media URL for tenant domains
FORCE_SCRIPT_NAME = None  # This allows media to work with tenant domains

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ]
}

JAZZMIN_SETTINGS = {
    "site_title": "DUKA YANGU POS Admin",
    "site_header": "DUKA YANGU POS",
    "site_brand": "DUKA YANGU POS",
    "welcome_sign": "Platform Owner Console",
    "copyright": "DUKA YANGU POS",
    "search_model": ["tenants.Client", "auth.User"],
    "show_ui_builder": False,
    "custom_css": "admin/css/custom_admin.css",
    "custom_js": "admin/js/scope_nav.js",

    "icons": {
        "auth": "fas fa-users-cog",
        "auth.group": "fas fa-users",
        "tenants.client": "fas fa-store",
        "tenants.domain": "fas fa-globe",
        "tenants.platformauditlog": "fas fa-clipboard-list",
        "inventory.product": "fas fa-box",
        "inventory.category": "fas fa-tags",
        "sales.sale": "fas fa-receipt",
        "users.user": "fas fa-user",
        "authtoken.tokenproxy": "fas fa-key",
    },

    "order_with_respect_to": ["tenants", "auth", "inventory", "sales", "users"],

    "topmenu_links": [
        {"name": "Home", "url": "admin:index"},
        {"name": "Stores", "model": "tenants.Client"},
        {"name": "Audit Log", "model": "tenants.PlatformAuditLog"},
    ],
}

JAZZMIN_UI_TWEAKS = {
    "theme": "flatly",
    "default_theme_mode": "light",
    "navbar": "navbar-dark",
    "navbar_fixed": True,
    "no_navbar_border": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_fixed": True,
    "accent": "accent-primary",
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success",
    },
}

# Payment gateway credentials — see .env.example
STRIPE_API_SECRET_KEY = env('STRIPE_API_SECRET_KEY', default='')
STRIPE_API_PUBLIC_KEY = env('STRIPE_API_PUBLIC_KEY', default='')
STRIPE_API_WEBHOOK_SECRET = env('STRIPE_API_WEBHOOK_SECRET', default='')

PAYPAL_CLIENT_ID = env('PAYPAL_CLIENT_ID', default='')
PAYPAL_CLIENT_SECRET = env('PAYPAL_CLIENT_SECRET', default='')
PAYPAL_MODE = env('PAYPAL_MODE', default='sandbox')

MPESA_CONSUMER_KEY = env('MPESA_CONSUMER_KEY', default='')
MPESA_CONSUMER_SECRET = env('MPESA_CONSUMER_SECRET', default='')
MPESA_SHORTCODE = env('MPESA_SHORTCODE', default='')
MPESA_PASSKEY = env('MPESA_PASSKEY', default='')
MPESA_ENV = env('MPESA_ENV', default='sandbox')
MPESA_CALLBACK_URL = env('MPESA_CALLBACK_URL', default='')

FRONTEND_SUCCESS_URL = env('FRONTEND_SUCCESS_URL', default='http://localhost:8000/billing/success/')
FRONTEND_CANCEL_URL = env('FRONTEND_CANCEL_URL', default='http://localhost:8000/billing/cancel/')