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
