import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_BOLD = Path(__file__).resolve().parents[1] / "assets" / "fonts" / "NotoSans-Bold.ttf"
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
              fill=(255, 255, 255, 200), anchor="mm")
    out = io.BytesIO()
    img.save(out, "WEBP", quality=80)
    return out.getvalue()
