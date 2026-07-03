import io

import cv2
import numpy as np
from PIL import Image


def remove_background_opencv(pil_image: Image.Image, margin_ratio: float = 0.06) -> Image.Image:
    rgb_image = pil_image.convert("RGB")
    cv_image = cv2.cvtColor(np.array(rgb_image), cv2.COLOR_RGB2BGR)
    height, width = cv_image.shape[:2]

    # GrabCut needs a reasonable amount of pixels to work with
    if height < 20 or width < 20:
        return rgb_image

    mask = np.zeros((height, width), np.uint8)
    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)

    margin_x = max(1, int(width * margin_ratio))
    margin_y = max(1, int(height * margin_ratio))
    rect = (margin_x, margin_y, width - 2 * margin_x, height - 2 * margin_y)

    try:
        cv2.grabCut(cv_image, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)
    except cv2.error:
        # Flat / low-contrast images can make GrabCut choke, keep the original
        return rgb_image

    binary_mask = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0).astype("uint8")

    # Sanity check: if GrabCut decided almost nothing (or everything) is the
    # foreground, it's likely misfired, better a normal photo than a botched cutout
    foreground_ratio = binary_mask.sum() / (height * width)
    if foreground_ratio < 0.02 or foreground_ratio > 0.98:
        return rgb_image

    # Soften the mask edges so the cutout doesn't look jagged
    soft_mask = cv2.GaussianBlur(binary_mask.astype("float32"), (5, 5), 0)
    soft_mask = np.clip(soft_mask, 0, 1)

    white_bg = np.full_like(cv_image, 255)
    mask_3ch = np.dstack([soft_mask] * 3)
    composited = (cv_image * mask_3ch + white_bg * (1 - mask_3ch)).astype("uint8")

    result_rgb = cv2.cvtColor(composited, cv2.COLOR_BGR2RGB)
    return Image.fromarray(result_rgb)


def compress_image(
    pil_image: Image.Image,
    target_kb: int = 100,
    hard_ceiling_kb: int = 150,
    min_quality: int = 35,
    max_dimension: int = 1600,
) -> bytes:
    """
    Re-encodes an image as JPEG, aiming for target_kb and never exceeding
    hard_ceiling_kb. Steps JPEG quality down first; if that alone can't hit
    the ceiling, downsizes the image as a last resort. Returns raw JPEG bytes.
    """
    image = pil_image.convert("RGB")

    # Cap resolution up front, catalog photos rarely need to be huge
    if max(image.size) > max_dimension:
        image.thumbnail((max_dimension, max_dimension), Image.LANCZOS)

    def encode(img: Image.Image, quality: int) -> bytes:
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        return buffer.getvalue()

    quality = 90
    data = encode(image, quality)

    while len(data) > target_kb * 1024 and quality > min_quality:
        quality -= 5
        data = encode(image, quality)

    # Still too big even at floor quality, shrink dimensions instead
    while len(data) > hard_ceiling_kb * 1024 and min(image.size) > 200:
        image = image.resize((int(image.width * 0.85), int(image.height * 0.85)), Image.LANCZOS)
        data = encode(image, max(min_quality, quality))

    return data


def process_product_photo(pil_image: Image.Image, target_kb: int = 100, hard_ceiling_kb: int = 150) -> bytes:
    """Convenience wrapper: background removal followed by compression."""
    cleaned = remove_background_opencv(pil_image)
    return compress_image(cleaned, target_kb=target_kb, hard_ceiling_kb=hard_ceiling_kb)