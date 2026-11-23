import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_BOLD = Path(__file__).resolve().parents[1] / "assets" / "fonts" / "NotoSans-Bold.ttf"
PHOTOS_DIR = Path(__file__).parent / "photos"  # owner-supplied demo photos; see photos/README.md
W, H = 1200, 900


def make_placeholder(label: str, color: str) -> bytes:
    """Labelled flat-colour placeholder (WebP bytes); the label uses the bundled Noto Sans so Turkish glyphs render."""
    img = Image.new("RGB", (W, H), color)
    draw = ImageDraw.Draw(img)
    size = 80
    font = ImageFont.truetype(str(FONT_BOLD), size)
    while size > 24 and draw.textlength(label, font=font) > W - 120:
        size -= 4
        font = ImageFont.truetype(str(FONT_BOLD), size)
    draw.text((W / 2, H / 2), label, font=font, fill="white", anchor="mm")
    draw.text((W / 2, H - 60), "ÖRNEK GÖRSEL / PLACEHOLDER", font=ImageFont.truetype(str(FONT_BOLD), 28),
              fill="#E6E6E6", anchor="mm")
    out = io.BytesIO()
    img.save(out, "WEBP", quality=80)
    return out.getvalue()


def demo_photo(spec_key: str, label: str, color: str) -> bytes:
    """The owner's photo for this label if present (same pipeline as uploads), else a labelled placeholder."""
    from app.services.storage_service import validate_and_process_image
    from app.services.storefront_service import slugify_tr
    for ext in ("jpg", "jpeg", "png", "webp"):
        f = PHOTOS_DIR / spec_key / f"{slugify_tr(label)}.{ext}"
        if f.is_file():
            return validate_and_process_image(f.read_bytes())
    return make_placeholder(label, color)
