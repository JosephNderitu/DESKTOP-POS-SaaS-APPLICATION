from django.core.management.base import BaseCommand
from billing.models import SubscriptionPlan

PLANS = [
    dict(code='starter-monthly', name='Starter', tagline='For a single till getting started',
         price_kes=1500, price_usd=12, billing_cycle='MONTHLY', max_terminals=1, max_staff=3,
         features=["1 POS terminal", "Up to 3 staff accounts", "Core inventory & sales", "Email support"], sort_order=1),
    dict(code='starter-yearly', name='Starter (Yearly)', tagline='2 months free, billed annually',
         price_kes=15000, price_usd=120, billing_cycle='YEARLY', max_terminals=1, max_staff=3,
         features=["1 POS terminal", "Up to 3 staff accounts", "Core inventory & sales", "Email support"], sort_order=2),
    dict(code='growth-monthly', name='Growth', tagline='For multi-till stores ready to scale',
         price_kes=3500, price_usd=28, billing_cycle='MONTHLY', max_terminals=3, max_staff=10,
         features=["Up to 3 terminals", "Up to 10 staff accounts", "Multi-branch inventory", "M-Pesa checkout", "Priority support"], sort_order=3),
    dict(code='growth-yearly', name='Growth (Yearly)', tagline='2 months free, billed annually',
         price_kes=35000, price_usd=280, billing_cycle='YEARLY', max_terminals=3, max_staff=10,
         features=["Up to 3 terminals", "Up to 10 staff accounts", "Multi-branch inventory", "M-Pesa checkout", "Priority support"], sort_order=4),
    dict(code='scale-monthly', name='Scale', tagline='For established retailers and chains',
         price_kes=7500, price_usd=60, billing_cycle='MONTHLY', max_terminals=999, max_staff=999,
         features=["Unlimited terminals", "Unlimited staff", "All payment gateways", "Advanced reporting", "Dedicated support"], sort_order=5),
    dict(code='scale-yearly', name='Scale (Yearly)', tagline='2 months free, billed annually',
         price_kes=75000, price_usd=600, billing_cycle='YEARLY', max_terminals=999, max_staff=999,
         features=["Unlimited terminals", "Unlimited staff", "All payment gateways", "Advanced reporting", "Dedicated support"], sort_order=6),
]


class Command(BaseCommand):
    help = "Seeds realistic subscription plans. Idempotent — safe to re-run any time pricing changes."

    def handle(self, *args, **options):
        for data in PLANS:
            plan, created = SubscriptionPlan.objects.update_or_create(code=data['code'], defaults=data)
            self.stdout.write(self.style.SUCCESS(f"{'Created' if created else 'Updated'}: {plan.name}"))