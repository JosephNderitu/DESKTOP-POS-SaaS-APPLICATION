from django.db import models
from core_backend.models_base import AbstractBaseUUIDModel
from inventory.models import Product
from django.conf import settings  # We will link this to our custom user model later

class Sale(AbstractBaseUUIDModel):
    STATUS_CHOICES = [
        ('COMPLETED', 'Completed'),
        ('PENDING', 'Pending/Hold'),
        ('CANCELLED', 'Cancelled'),
    ]

    # Cashier mapping (using AUTH_USER_MODEL to refer to our users app)
    cashier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sales")
    
    # Totals
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='COMPLETED')
    
    # Metadata for offline identification
    offline_created_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when recorded on desktop client clock")

    class Meta:
        ordering = ['-created_at']  # latest first, everywhere this model is queried — not just in admin
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['cashier']),
        ]

    def __str__(self):
        return f"Sale {str(self.id)[:8]} - Total: {self.total_amount}"


class SaleItem(AbstractBaseUUIDModel):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="sale_items")
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, help_text="Selling price at the exact moment of purchase")
    cost_price = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Product cost price at the exact moment of purchase — used for profit margin reporting, frozen so later cost changes don't distort historical margins."
    )
    total_price = models.DecimalField(max_digits=12, decimal_places=2)

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class Payment(AbstractBaseUUIDModel):
    PAYMENT_METHODS = [
        ('CASH', 'Cash'),
        ('MPESA', 'M-Pesa'),
        ('STRIPE', 'Stripe / Card'),
        ('PAYPAL', 'PayPal'),
    ]

    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="payments")
    method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Transaction references for external financial gateways
    transaction_reference = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        help_text="M-Pesa Receipt Code or Stripe Charge ID"
    )
    
    # Open field for payment gateway callback logs/error handling
    gateway_response = models.JSONField(blank=True, null=True, help_text="Full response dumped from payment provider API")

    def __str__(self):
        return f"{self.method} Payment of {self.amount} for Sale {self.sale.id}"