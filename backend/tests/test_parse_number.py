import shutil
import subprocess
from pathlib import Path

import pytest

CHECK = Path(__file__).resolve().parents[2] / "frontend" / "src" / "i18n" / "parseNumber.check.ts"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_parse_number_cases():
    r = subprocess.run(["node", "--experimental-strip-types", str(CHECK)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
