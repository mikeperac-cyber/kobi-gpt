from fastapi import HTTPException


async def require_admin():
    # Stub: Task 3 implements real auth; until then nobody is an admin.
    raise HTTPException(403, {"code": "forbidden", "message_key": "errors.forbidden"})
