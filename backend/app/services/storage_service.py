import io
import uuid
from pathlib import Path
from typing import Protocol

from PIL import Image, ImageOps

MAX_BYTES = 8 * 1024 * 1024
MAX_SIDE = 1600
DEFAULT_ROOT = Path(__file__).resolve().parents[3] / "uploads"
_root: Path | None = None


def set_root(path: Path | None) -> None:  # tests point this at tmp_path
    global _root
    _root = path


class Storage(Protocol):
    async def save(self, data: bytes, prefix: str) -> str: ...
    async def delete(self, url: str) -> None: ...


class LocalStorage:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    async def save(self, data: bytes, prefix: str) -> str:
        folder = self.root / prefix
        folder.mkdir(parents=True, exist_ok=True)
        name = f"{uuid.uuid4().hex}.webp"  # never the client's filename
        (folder / name).write_bytes(data)
        return f"/uploads/{prefix}/{name}"

    def read(self, url: str) -> bytes | None:
        """Bytes of a stored upload, or None; only files under the storage root are ever read."""
        path = (self.root / url.removeprefix("/uploads/")).resolve()
        if not url.startswith("/uploads/") or not path.is_relative_to(self.root) or not path.is_file():
            return None
        return path.read_bytes()

    async def delete(self, url: str) -> None:
        path = (self.root / url.removeprefix("/uploads/")).resolve()
        if not url.startswith("/uploads/") or not path.is_relative_to(self.root):
            raise ValueError("url outside storage root")
        path.unlink(missing_ok=True)


def get_storage() -> Storage:
    return LocalStorage(_root or DEFAULT_ROOT)


def validate_and_process_image(data: bytes) -> bytes:
    if len(data) > MAX_BYTES:
        raise ValueError("too_large")
    if not (data.startswith((b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n")) or (data[:4] == b"RIFF" and data[8:12] == b"WEBP")):
        raise ValueError("bad_type")
    try:
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))
        img.load()
    except (Image.DecompressionBombError, OSError, ValueError, SyntaxError):
        raise ValueError("bad_type") from None
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA" if img.mode in ("LA", "PA") or "transparency" in img.info else "RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    out = io.BytesIO()
    img.save(out, "WEBP", quality=80)
    return out.getvalue()
