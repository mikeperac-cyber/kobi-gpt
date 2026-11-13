from datetime import date, datetime
from typing import Any

from bson import ObjectId


def to_json(value: Any) -> Any:
    """Mongo doc -> JSON-safe: `_id` becomes `id`, ObjectId/datetime become str."""
    if isinstance(value, dict):
        return {("id" if k == "_id" else k): to_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_json(v) for v in value]
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value
