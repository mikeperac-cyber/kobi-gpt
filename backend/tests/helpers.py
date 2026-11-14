def assert_no_floor(obj, path="$"):
    """Fail if the key `price_floor` appears anywhere in a JSON-like structure."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            assert k != "price_floor", f"price_floor leaked at {path}"
            assert_no_floor(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            assert_no_floor(v, f"{path}[{i}]")


def load_kb_json(name):
    import json
    from pathlib import Path
    return json.loads((Path(__file__).resolve().parents[1] / "app" / "seed" / "data" / f"{name}.json")
                      .read_text(encoding="utf-8"))
