from django.db import migrations


def backfill_cost_price(apps, schema_editor):
    SaleItem = apps.get_model("sales", "SaleItem")

    for item in SaleItem.objects.select_related("product").filter(cost_price=0):
        if item.product_id:
            item.cost_price = item.product.cost_price
            item.save(update_fields=["cost_price"])


class Migration(migrations.Migration):

    dependencies = [
        ("sales", "0004_saleitem_cost_price_alter_saleitem_unit_price"),
    ]

    operations = [
        migrations.RunPython(backfill_cost_price, migrations.RunPython.noop),
    ]