from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models import Count, Max
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django_tenants.utils import get_public_schema_name

from .models import Client, LoginEvent, log_platform_action

RANGE_DAYS = {
    'week': 7,
    'month': 30,
    'quarter': 90,
    '6months': 182,
    'year': 365,
}

RANGE_GRANULARITY = {
    'week': 'day',
    'month': 'day',
    'quarter': 'week',
    '6months': 'month',
    'year': 'month',
}

TRUNC_FUNCS = {
    'day': TruncDate,
    'week': TruncWeek,
    'month': TruncMonth,
}

ENGAGEMENT_LABELS = {
    'ACTIVE': 'Active (last 7 days)',
    'IDLE': 'Idle (8–30 days)',
    'INACTIVE': 'Inactive (31–90 days)',
    'DORMANT': 'Dormant (90+ days / never)',
}

ENGAGEMENT_COLORS = {
    'ACTIVE': '#008C72',
    'IDLE': '#F59E0B',
    'INACTIVE': '#EA580C',
    'DORMANT': '#DC2626',
}

SUBSCRIPTION_LABELS = {
    'TRIAL': 'Trial',
    'PENDING_PAYMENT': 'Pending Payment',
    'ACTIVE': 'Active',
    'SUSPENDED': 'Suspended',
    'TERMINATED': 'Terminated',
}

SUBSCRIPTION_COLORS = {
    'TRIAL': '#F59E0B',
    'PENDING_PAYMENT': '#EA580C',
    'ACTIVE': '#008C72',
    'SUSPENDED': '#DC2626',
    'TERMINATED': '#7F1D1D',
}


def _require_platform_owner(request):
    """
    True only for a superuser whose request resolved to the public schema.
    Store-level superusers structurally can't reach this at all (their own
    subdomain never routes to core_backend.urls) — this check is defense in
    depth on top of that isolation, matching IsPlatformOwner's logic for the
    DRF platform endpoints. Plain Django views (not DRF APIView) are used
    throughout this module deliberately: this page is session-cookie
    authenticated (the admin dashboard's own JS calling its own API), not
    token-authenticated, so DRF's default TokenAuthentication would reject
    every call here if these were APIViews.
    """
    return (
        request.user.is_authenticated
        and request.user.is_superuser
        and getattr(request, 'tenant', None) is not None
        and request.tenant.schema_name == get_public_schema_name()
    )


def _classify_engagement(days_inactive):
    if days_inactive is None:
        return 'DORMANT'  # never logged in at all
    if days_inactive <= 7:
        return 'ACTIVE'
    if days_inactive <= 30:
        return 'IDLE'
    if days_inactive <= 90:
        return 'INACTIVE'
    return 'DORMANT'


def _format_bucket_label(bucket, granularity):
    if granularity == 'day':
        return bucket.strftime('%b %d')
    if granularity == 'week':
        return f"Wk of {bucket.strftime('%b %d')}"
    return bucket.strftime('%b %Y')


def platform_login_timeseries_api(request):
    """
    GET /api/v1/platform/analytics/login-timeseries/?range=week|month|quarter|6months|year

    Total login events across every store, bucketed over time. A single
    query against the public-schema LoginEvent table — no per-tenant
    looping needed, since every login already lands here regardless of
    which store it happened at.
    """
    if not _require_platform_owner(request):
        return JsonResponse({"error": "Forbidden"}, status=403)

    range_key = request.GET.get('range', 'month')
    days = RANGE_DAYS.get(range_key, 30)
    granularity = RANGE_GRANULARITY.get(range_key, 'day')
    trunc_func = TRUNC_FUNCS[granularity]
    since = timezone.now() - timedelta(days=days)

    series_qs = (
        LoginEvent.objects.filter(timestamp__gte=since)
        .annotate(bucket=trunc_func('timestamp'))
        .values('bucket')
        .annotate(count=Count('id'))
        .order_by('bucket')
    )
    labels = [_format_bucket_label(row['bucket'], granularity) for row in series_qs]
    values = [row['count'] for row in series_qs]

    return JsonResponse({"range": range_key, "labels": labels, "values": values})


def platform_store_activity_api(request):
    """
    GET /api/v1/platform/analytics/store-activity/?range=week|month|quarter|6months|year

    Per-store rollup: last login, days since, an engagement classification
    derived from that, login count in the selected range, subscription
    status/plan, and cashier count.

    Cashier counts now read Client.cashier_count directly — a cached field
    kept in sync by users.signals whenever a store's staff list changes —
    rather than entering every tenant's schema on every page load. That
    cross-schema loop was fine at small scale but was flagged as the one
    part of this endpoint that wouldn't stay fast as store counts grew;
    this removes it entirely.

    Engagement changes ARE still detected here and written back to
    Client.last_known_engagement, with a PlatformAuditLog entry logged the
    moment a store's classification changes — this gives a real timeline of
    when stores went quiet instead of only ever seeing a snapshot.
    """
    if not _require_platform_owner(request):
        return JsonResponse({"error": "Forbidden"}, status=403)

    range_key = request.GET.get('range', 'month')
    days = RANGE_DAYS.get(range_key, 30)
    since = timezone.now() - timedelta(days=days)
    now = timezone.now()

    tenants = Client.objects.exclude(schema_name=get_public_schema_name())

    last_login_map = {
        row['tenant_schema']: row['last_login']
        for row in LoginEvent.objects.values('tenant_schema').annotate(last_login=Max('timestamp'))
    }
    range_count_map = {
        row['tenant_schema']: row['count']
        for row in (
            LoginEvent.objects.filter(timestamp__gte=since)
            .values('tenant_schema')
            .annotate(count=Count('id'))
        )
    }

    stores = []
    engagement_breakdown = {'ACTIVE': 0, 'IDLE': 0, 'INACTIVE': 0, 'DORMANT': 0}
    subscription_breakdown = {}
    total_cashiers = 0

    for tenant in tenants:
        last_login = last_login_map.get(tenant.schema_name)
        days_inactive = (now - last_login).days if last_login else None
        engagement = _classify_engagement(days_inactive)
        engagement_breakdown[engagement] += 1

        subscription_breakdown[tenant.subscription_status] = (
            subscription_breakdown.get(tenant.subscription_status, 0) + 1
        )

        # Detect and log an engagement change. Skip the very first
        # classification a store ever gets (last_known_engagement == '') —
        # that's not a "change", it's just the initial value, and logging
        # it would clutter the audit log with a noise entry per store the
        # first time this endpoint ever runs.
        if tenant.last_known_engagement and tenant.last_known_engagement != engagement:
            log_platform_action(
                'system',
                f'ENGAGEMENT_CHANGED:{tenant.last_known_engagement}->{engagement}',
                tenant.schema_name,
                f"Days inactive: {days_inactive if days_inactive is not None else 'never logged in'}",
            )
        if tenant.last_known_engagement != engagement:
            tenant.last_known_engagement = engagement
            tenant.save(update_fields=['last_known_engagement'])

        total_cashiers += tenant.cashier_count

        stores.append({
            "schema_name": tenant.schema_name,
            "name": tenant.name,
            "subscription_status": tenant.subscription_status,
            "subscription_plan": tenant.subscription_plan,
            "last_login": last_login.isoformat() if last_login else None,
            "days_inactive": days_inactive,
            "logins_in_range": range_count_map.get(tenant.schema_name, 0),
            "cashier_count": tenant.cashier_count,
            "engagement": engagement,
        })

    # Most-inactive first — that's the list a platform owner actually needs
    # to act on (who to flag, who to message).
    stores.sort(key=lambda s: (s['days_inactive'] is None, s['days_inactive'] or 0), reverse=True)

    return JsonResponse({
        "range": range_key,
        "stores": stores,
        "summary": {
            "engagement_breakdown": engagement_breakdown,
            "subscription_breakdown": subscription_breakdown,
            "total_cashiers": total_cashiers,
            "total_stores": len(stores),
        },
    })


def send_inactivity_reminder(request, schema_name):
    """
    POST /api/v1/platform/stores/<schema_name>/send-reminder/

    Sends a "we miss you" email to the store's owner_email using the same
    SMTP configuration already set up for password-reset emails — no new
    infrastructure needed. Logs a PlatformAuditLog entry so there's a
    record of when reminders were sent and to whom.
    """
    if request.method != 'POST':
        return JsonResponse({"error": "POST required."}, status=405)
    if not _require_platform_owner(request):
        return JsonResponse({"error": "Forbidden"}, status=403)

    tenant = Client.objects.filter(schema_name=schema_name).exclude(schema_name=get_public_schema_name()).first()
    if not tenant:
        return JsonResponse({"error": "Store not found."}, status=404)
    if not tenant.owner_email:
        return JsonResponse({"error": "This store has no owner email on file."}, status=400)

    last_login = LoginEvent.objects.filter(tenant_schema=schema_name).aggregate(last=Max('timestamp'))['last']
    days_inactive = (timezone.now() - last_login).days if last_login else None

    html_body = render_to_string('emails/inactivity_reminder.html', {
        'store_name': tenant.name,
        'days_inactive': days_inactive,
    })
    message = EmailMultiAlternatives(
        subject=f"We miss you at {tenant.name} — come back to RVC POS",
        body=(
            f"We noticed {tenant.name} hasn't been used in a while. "
            "Log back in to keep your store running smoothly."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[tenant.owner_email],
    )
    message.attach_alternative(html_body, "text/html")
    message.send(fail_silently=True)

    log_platform_action(
        request.user, 'INACTIVITY_REMINDER_SENT', tenant.schema_name,
        f"Sent to {tenant.owner_email}, days inactive: {days_inactive if days_inactive is not None else 'never logged in'}",
    )

    return JsonResponse({"success": True, "message": f"Reminder email sent to {tenant.owner_email}."})