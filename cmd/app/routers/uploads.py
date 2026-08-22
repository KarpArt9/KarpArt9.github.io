from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.auth import require_admin
from app.config import settings

router = APIRouter()

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_SIZE = 5 * 1024 * 1024


@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    _admin: str = Depends(require_admin),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Допустимы только jpg, png, webp")

    data = await file.read()
    if len(data) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="Файл больше 5 МБ")
    if not data:
        raise HTTPException(status_code=400, detail="Пустой файл")

    name = f"{uuid4().hex}{ext}"
    path = settings.upload_dir / name
    path.write_bytes(data)
    return {"url": f"/uploads/{name}"}
