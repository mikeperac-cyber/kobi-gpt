import shutil
import subprocess
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_whatsapp_link_cases():
    r = subprocess.run(["node", "--experimental-strip-types", str(SRC / "storefront" / "whatsapp.check.ts")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_vercel_bot_rule_spares_search_engines():
    """Search engines render the SPA themselves; the share page's instant refresh would look like a redirect loop."""
    import json
    rules = json.loads((SRC.parent / "vercel.json").read_text(encoding="utf-8"))["rewrites"]
    bot = next(r for r in rules if r.get("has"))
    ua = bot["has"][0]["value"]
    assert "WhatsApp" in ua and "facebookexternalhit" in ua
    assert "Googlebot" not in ua and "bingbot" not in ua
