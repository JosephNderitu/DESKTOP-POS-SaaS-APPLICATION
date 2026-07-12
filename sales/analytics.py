import calendar
from datetime import datetime, timedelta

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek
from django.http import JsonResponse
from django.utils import timezone

from .models import Payment, Sale, SaleItem

RANGE_DAYS = {
    'week': 7,
    'month': 30,
    'quarter': 90,
    '6months': 182,
    'year': 365,
}

# How finely to bucket the line graph per range — daily buckets over a full
# year would be 365 points and unreadable, so longer ranges roll up coarser.
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

PAYMENT_LABELS = {
    'CASH': 'Cash',
    'MPESA': 'M-Pesa',
    'STRIPE': 'Stripe',
    'PAYPAL': 'PayPal',
}

PAYMENT_COLORS = {
    'CASH': '#059669',
    'MPESA': '#00A651',
    'STRIPE': '#635BFF',
    'PAYPAL': '#0070BA',
}

_PROFIT_EXPR = ExpressionWrapper(
    (F('unit_price') - F('cost_price')) * F('quantity'),
    output_field=DecimalField(max_digits=14, decimal_places=2),
)


def _require_staff(request):
    return request.user.is_authenticated and request.user.is_staff


def _format_bucket_label(bucket, granularity):
    if granularity == 'day':
        return bucket.strftime('%b %d')
    if granularity == 'week':
        return f"Wk of {bucket.strftime('%b %d')}"
    return bucket.strftime('%b %Y')


def _period_totals(start, end=None):
    """
    Aggregates gross/net/discount/profit/transaction-count for a window.
    end=None means open-ended (up to now) — used for the "current" period;
    a bounded [start, end) window is used for the "previous" period so the
    two never overlap.
    """
    sale_filters = {'created_at__gte': start, 'status': 'COMPLETED'}
    item_filters = {'sale__created_at__gte': start, 'sale__status': 'COMPLETED'}
    if end is not None:
        sale_filters['created_at__lt'] = end
        item_filters['sale__created_at__lt'] = end

    sales_qs = Sale.objects.filter(**sale_filters)
    totals = sales_qs.aggregate(
        gross_sales=Sum('subtotal'),
        total_discounts=Sum('discount_amount'),
        net_sales=Sum('total_amount'),
    )
    transaction_count = sales_qs.count()

    profit_agg = SaleItem.objects.filter(**item_filters).aggregate(gross_profit=Sum(_PROFIT_EXPR))
    gross_profit = float(profit_agg['gross_profit'] or 0)
    net_sales = float(totals['net_sales'] or 0)
    margin_pct = round((gross_profit / net_sales * 100), 1) if net_sales > 0 else 0.0

    return {
        "gross_sales": float(totals['gross_sales'] or 0),
        "total_discounts": float(totals['total_discounts'] or 0),
        "net_sales": net_sales,
        "transaction_count": transaction_count,
        "gross_profit": gross_profit,
        "margin_pct": margin_pct,
    }


def _pct_delta(current, previous):
    """
    None means "no meaningful comparison" (nothing happened in the previous
    period, so a percentage change is undefined rather than misleadingly
    huge/zero) — the frontend renders that as a neutral "New" badge instead
    of a fabricated number.
    """
    if previous == 0:
        return None
    return round((current - previous) / previous * 100, 1)


def sales_analytics_api(request):
    """
    GET /api/v1/sales/analytics/?range=week|month|quarter|6months|year

    Session-authenticated (called from the admin dashboard's own page, not
    the desktop client), so a plain is_staff check is used rather than DRF
    token auth. Returns totals (including gross profit + margin), a
    payment-method breakdown (pie chart), a time-series (line chart), and
    period-over-period deltas comparing this window to the equal-length
    window immediately before it.
    """
    if not _require_staff(request):
        return JsonResponse({"error": "Forbidden"}, status=403)

    range_key = request.GET.get('range', 'month')
    days = RANGE_DAYS.get(range_key, 30)
    granularity = RANGE_GRANULARITY.get(range_key, 'day')
    trunc_func = TRUNC_FUNCS[granularity]

    now = timezone.now()
    since = now - timedelta(days=days)
    previous_since = since - timedelta(days=days)

    current_totals = _period_totals(since)
    previous_totals = _period_totals(previous_since, since)
    deltas = {
        key: _pct_delta(current_totals[key], previous_totals[key])
        for key in ('gross_sales', 'net_sales', 'total_discounts', 'transaction_count', 'gross_profit')
    }

    sales_qs = Sale.objects.filter(created_at__gte=since, status='COMPLETED')

    # --- Payment-method breakdown (pie chart) ---
    breakdown_qs = (
        Payment.objects
        .filter(sale__created_at__gte=since, sale__status='COMPLETED')
        .values('method')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )
    pie_labels = [PAYMENT_LABELS.get(row['method'], row['method'].title()) for row in breakdown_qs]
    pie_values = [float(row['total']) for row in breakdown_qs]
    pie_colors = [PAYMENT_COLORS.get(row['method'], '#64748B') for row in breakdown_qs]

    # --- Time series (line chart) ---
    series_qs = (
        sales_qs
        .annotate(bucket=trunc_func('created_at'))
        .values('bucket')
        .annotate(gross=Sum('subtotal'), net=Sum('total_amount'))
        .order_by('bucket')
    )
    timeseries_labels = [_format_bucket_label(row['bucket'], granularity) for row in series_qs]
    timeseries_gross = [float(row['gross'] or 0) for row in series_qs]
    timeseries_net = [float(row['net'] or 0) for row in series_qs]

    return JsonResponse({
        "range": range_key,
        "labels": pie_labels,
        "values": pie_values,
        "colors": pie_colors,
        "totals": current_totals,
        "deltas": deltas,
        "timeseries": {
            "labels": timeseries_labels,
            "gross": timeseries_gross,
            "net": timeseries_net,
        },
    })


def cashier_performance_api(request):
    """
    GET /api/v1/sales/cashier-performance/?month=YYYY-MM

    Ranks cashiers by net sales for a single calendar month — deliberately
    month-scoped rather than tied to the week/quarter/year range selector
    above, since commission decisions are made monthly. Defaults to the
    current month if none is given.
    """
    if not _require_staff(request):
        return JsonResponse({"error": "Forbidden"}, status=403)

    month_param = request.GET.get('month')
    now = timezone.localtime(timezone.now())

    if month_param:
        try:
            year, month = (int(part) for part in month_param.split('-'))
            if not (1 <= month <= 12):
                raise ValueError
        except (ValueError, AttributeError):
            return JsonResponse({"error": "month must be in YYYY-MM format."}, status=400)
    else:
        year, month = now.year, now.month

    start = timezone.make_aware(datetime(year, month, 1))
    last_day = calendar.monthrange(year, month)[1]
    end = timezone.make_aware(datetime(year, month, last_day, 23, 59, 59))

    sales_qs = Sale.objects.filter(created_at__gte=start, created_at__lte=end, status='COMPLETED')

    performance_qs = (
        sales_qs
        .values('cashier__id', 'cashier__username')
        .annotate(net_sales=Sum('total_amount'), transaction_count=Count('id'))
        .order_by('-net_sales')
    )

    cashiers = [
        {
            "cashier_id": str(row['cashier__id']),
            "username": row['cashier__username'],
            "net_sales": float(row['net_sales'] or 0),
            "transaction_count": row['transaction_count'],
        }
        for row in performance_qs
    ]

    return JsonResponse({
        "month": f"{year:04d}-{month:02d}",
        "month_label": start.strftime('%B %Y'),
        "cashiers": cashiers,
    })