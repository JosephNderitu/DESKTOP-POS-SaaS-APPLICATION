from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction as db_transaction

from inventory.models import Product

from .models import Sale, SaleItem


class CheckoutError(Exception):
    """Raised for any checkout validation failure — empty cart, insufficient
    stock, inactive product, stock changed before payment confirmed, etc.
    The message is written to be shown directly to the cashier."""
    pass


def compute_unit_price(product):
    """
    Applies the product's active discount using the exact same rule the
    desktop client uses for display (ProductCardWidget), so the price a
    cashier sees on a product card always matches what actually gets
    charged at checkout. Server-side and authoritative — never trusts a
    price sent from the client.
    """
    selling_price = product.selling_price
    discount = product.product_discount or Decimal('0')
    if discount > 0:
        discounted = selling_price * (Decimal('1') - discount / Decimal('100'))
        return discounted.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return selling_price


def build_sale_from_cart(items_payload, cashier):
    """
    items_payload: [{"product_id": "...", "quantity": 2}, ...]

    Validates stock and computes discount-aware pricing entirely server-side,
    then creates the Sale + SaleItem rows in PENDING status. Stock is NOT
    decremented here — that only happens once payment is actually confirmed
    (see finalize_sale), so an abandoned Stripe or M-Pesa checkout never
    locks up inventory that was never actually paid for.
    """
    if not items_payload:
        raise CheckoutError("Cart is empty.")

    subtotal = Decimal('0.00')
    discount_amount = Decimal('0.00')
    line_data = []

    for entry in items_payload:
        product_id = entry.get('product_id')
        try:
            quantity = int(entry.get('quantity', 0))
        except (TypeError, ValueError):
            raise CheckoutError("Invalid quantity in cart.")

        if quantity <= 0:
            raise CheckoutError("Item quantity must be at least 1.")

        try:
            product = Product.objects.get(pk=product_id, is_active=True)
        except Product.DoesNotExist:
            raise CheckoutError("One of the items in this cart is no longer available.")

        if product.stock_quantity < quantity:
            raise CheckoutError(
                f"Not enough stock for '{product.name}' (have {product.stock_quantity}, need {quantity})."
            )

        full_price = product.selling_price
        unit_price = compute_unit_price(product)

        subtotal += full_price * quantity
        discount_amount += (full_price - unit_price) * quantity
        line_data.append((product, quantity, unit_price))

    total_amount = subtotal - discount_amount

    with db_transaction.atomic():
        sale = Sale.objects.create(
            cashier=cashier,
            subtotal=subtotal,
            discount_amount=discount_amount,
            tax_amount=Decimal('0.00'),
            total_amount=total_amount,
            status='PENDING',
        )
        for product, quantity, unit_price in line_data:
            SaleItem.objects.create(sale=sale, product=product, quantity=quantity, unit_price=unit_price)

    return sale


def finalize_sale(sale):
    """
    Marks a sale COMPLETED and decrements stock. Called immediately for cash
    (payment already happened physically), or from a gateway confirm/webhook
    for Stripe/M-Pesa. select_for_update guards against two near-simultaneous
    confirmations double-decrementing stock, and is itself idempotent — a
    webhook that fires twice for the same sale is a no-op the second time.
    """
    if sale.status == 'COMPLETED':
        return

    with db_transaction.atomic():
        for item in sale.items.select_related('product').select_for_update():
            product = item.product
            if product.stock_quantity < item.quantity:
                # Stock moved between checkout and payment confirmation
                # (e.g. another sale beat this one to it). Leave the sale
                # PENDING rather than selling stock that no longer exists.
                raise CheckoutError(
                    f"Stock for '{product.name}' changed before payment completed. This sale needs manual review."
                )
            product.stock_quantity -= item.quantity
            product.save(update_fields=['stock_quantity'])

        sale.status = 'COMPLETED'
        sale.save(update_fields=['status'])