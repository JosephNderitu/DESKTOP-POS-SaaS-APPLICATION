# Create your models here.
from django.core.files.base import ContentFile
from django.db import models

from core_backend.models_base import AbstractBaseUUIDModel

SIZE_TARGET_KB = 100
SIZE_CEILING_KB = 150


class Category(AbstractBaseUUIDModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Product(AbstractBaseUUIDModel):
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="products")
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, unique=True, help_text="Stock Keeping Unit / Barcode")
    description = models.TextField(blank=True, null=True)
    product_image = models.ImageField(upload_to='product_images/', blank=True, null=True, help_text="Optional product image")

    # Pricing fields (Using Decimal instead of Float to prevent rounding errors in currency)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, help_text="Buying price from supplier")
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, help_text="Retail price to customer")
    product_discount = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text="Discount percentage (e.g., 10 for 10%)")

    # Stock tracking
    stock_quantity = models.IntegerField(default=0)
    low_stock_threshold = models.IntegerField(default=5, help_text="Alert manager when stock dips below this")

    is_active = models.BooleanField(default=True)

    image_processed = models.BooleanField(default=False, editable=False)

    def __str__(self):
        return f"{self.name} ({self.sku})"

    def save(self, *args, **kwargs):
        self._maybe_process_image()
        super().save(*args, **kwargs)

    def _maybe_process_image(self):
        """
        Runs background removal + compression the first time an image is
        attached, or whenever it's swapped for a different file. Cheap saves
        that don't touch product_image (stock updates, price edits, etc.)
        skip this entirely.
        """
        if not self.product_image:
            self.image_processed = False
            return

        image_changed = True
        if self.pk:
            try:
                previous = Product.objects.only("product_image", "image_processed").get(pk=self.pk)
                image_changed = previous.product_image.name != self.product_image.name
                if not image_changed and previous.image_processed:
                    self.image_processed = True
                    return
            except Product.DoesNotExist:
                pass  # brand new row that already has a pk assigned (e.g. UUID pk)

        if not image_changed and self.image_processed:
            return

        # Deferred import: keeps OpenCV/Pillow out of the import path for
        # anything that doesn't actually save a Product with an image
        from PIL import Image as PILImage

        from .image_processing import process_product_photo

        try:
            self.product_image.open()
            pil_image = PILImage.open(self.product_image)
            pil_image.load()

            processed_bytes = process_product_photo(
                pil_image, target_kb=SIZE_TARGET_KB, hard_ceiling_kb=SIZE_CEILING_KB
            )

            original_name = self.product_image.name.rsplit("/", 1)[-1]
            base_name = original_name.rsplit(".", 1)[0]
            new_name = f"{base_name}_processed.jpg"

            # save=False: we're inside our own save(), the outer super().save()
            # call persists everything (including this field) in one go
            self.product_image.save(new_name, ContentFile(processed_bytes), save=False)
            self.image_processed = True
        except Exception:
            # A corrupt upload or processing failure shouldn't block the save
            # of the product itself, keep the original image and move on.
            # TODO: replace with proper logging once logging is wired up.
            self.image_processed = False
        finally:
            try:
                self.product_image.close()
            except Exception:
                pass