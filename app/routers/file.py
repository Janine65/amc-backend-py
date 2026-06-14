"""``files`` router – upload/download endpoints."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.config import get_config
from app.core.logging import get_logger
from app.dependencies import CurrentUser
from app.schemas.ret_data import RetDataFile, RetDataFilePayload

logger = get_logger(__name__)

router = APIRouter(prefix="/files", tags=["Files"])

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
MAX_SIZE = 50 * 1024 * 1024  # 50 MB


@router.get("/download")
async def download(filename: str, _: CurrentUser) -> FileResponse:
    cfg = get_config()
    file_path = Path(cfg.exports) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream",
    )


@router.post("/upload", response_model=RetDataFile)
async def upload(_: CurrentUser, file: UploadFile = File(...)) -> RetDataFile:
    if file is None:
        raise HTTPException(status_code=400, detail="no file uploaded")
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="invalid file type")

    cfg = get_config()
    Path(cfg.uploads).mkdir(parents=True, exist_ok=True)
    target = os.path.join(cfg.uploads, file.filename or "upload.bin")

    size = 0
    with open(target, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_SIZE:
                out.close()
                os.remove(target)
                raise HTTPException(status_code=400, detail="file is too large!")
            out.write(chunk)

    return RetDataFile(
        data=RetDataFilePayload(filename=file.filename or "upload.bin"),
        message="file uploaded",
    )
