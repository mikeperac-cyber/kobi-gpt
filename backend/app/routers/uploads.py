from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core.security import current_user
from app.services.storage_service import MAX_BYTES, get_storage, validate_and_process_image

router = APIRouter(prefix="/uploads")


def _err(code: str) -> HTTPException:
    return HTTPException(422, {"code": code, "message_key": f"errors.{code}"})


@router.post("/image")
async def upload_image(
    file: Annotated[UploadFile, File()],
    prefix: Annotated[Literal["products", "logos"], Form()] = "products",
    _user: dict = Depends(current_user),
):
    data = await file.read(MAX_BYTES + 1)  # bounded read, size checked before decoding
    try:
        processed = validate_and_process_image(data)
    except ValueError as e:
        raise _err(str(e)) from None
    return {"url": await get_storage().save(processed, prefix)}
