from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core.db import get_db
from app.core.security import current_user
from app.services.upload_registry import record_upload
from app.services.storage_service import MAX_BYTES, get_storage, validate_and_process_image, validate_document

router = APIRouter(prefix="/uploads")


def _err(code: str) -> HTTPException:
    return HTTPException(422, {"code": code, "message_key": f"errors.{code}"})


@router.post("/image")
async def upload_image(
    file: Annotated[UploadFile, File()],
    prefix: Annotated[Literal["products", "logos"], Form()] = "products",
    user: dict = Depends(current_user),
):
    data = await file.read(MAX_BYTES + 1)  # bounded read, size checked before decoding
    try:
        processed = validate_and_process_image(data)
    except ValueError as e:
        raise _err(str(e)) from None
    url = await get_storage().save(processed, prefix)
    await record_upload(get_db(), url, str(user["_id"]))
    return {"url": url}


@router.post("/document")
async def upload_document(file: Annotated[UploadFile, File()], user: dict = Depends(current_user)):
    """Private supplier documents (tax plate, certificates): stored under documents/, never served statically."""
    data = await file.read(MAX_BYTES + 1)
    try:
        processed, ext = validate_document(data)
    except ValueError as e:
        raise _err(str(e)) from None
    url = await get_storage().save_file(processed, f"documents/{user['_id']}", ext)
    await record_upload(get_db(), url, str(user["_id"]))
    return {"url": url}
