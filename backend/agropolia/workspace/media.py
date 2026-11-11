from __future__ import annotations

import io
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from PIL import Image, UnidentifiedImageError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from agropolia.auth.dependencies import TenantContext, get_tenant_context
from agropolia.config import get_settings
from agropolia.db import get_db
from agropolia.errors import DomainError
from agropolia.ids import uuid7

from .models import Media
from .service import assert_owner, owned_observation, owned_task

router = APIRouter(tags=["private-media"])

MAX_INPUT_BYTES = 12 * 1024 * 1024
MAX_OUTPUT_BYTES = 1_500_000


class LocalMediaStore:
    """Development/test only: replaceable private storage adapter."""
    def __init__(self, root: str):
        self.root = Path(root)

    def write(self, key: str, data: bytes):
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def read(self, key: str) -> bytes:
        return (self.root / key).read_bytes()


class S3MediaStore:
    def __init__(self):
        import boto3
        settings = get_settings()
        self.bucket = settings.s3_bucket
        self.client = boto3.client(
            "s3", endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
        )

    def write(self, key: str, data: bytes):
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType="image/jpeg")

    def read(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()


def store():
    settings = get_settings()
    if settings.media_storage == "s3":
        return S3MediaStore()
    return LocalMediaStore(settings.media_dir)


def compress_photo(raw: bytes) -> bytes:
    if len(raw) > MAX_INPUT_BYTES:
        raise DomainError("MEDIA_TOO_LARGE", "Фото превышает 12 МБ", 413)
    try:
        with Image.open(io.BytesIO(raw)) as src:
            src.verify()
        with Image.open(io.BytesIO(raw)) as src:
            if src.width * src.height > 40_000_000:
                raise DomainError("MEDIA_TOO_LARGE", "Слишком большое разрешение фото", 413)
            # The private copy preserves original EXIF metadata; public previews
            # are out of scope. Access is checked on every media read.
            exif = src.getexif().tobytes()
            picture = src.convert("RGB")
            for quality in (86, 78, 68, 58, 48, 36):
                out = io.BytesIO()
                picture.save(out, format="JPEG", quality=quality, optimize=True, exif=exif)
                if out.tell() <= MAX_OUTPUT_BYTES:
                    return out.getvalue()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise DomainError("UNSUPPORTED_MEDIA", "Загрузите фото JPEG, PNG или WebP", 422) from exc
    raise DomainError("MEDIA_TOO_LARGE", "Фото невозможно сжать до 1,5 МБ", 413)


async def require_owner(context: TenantContext, db: AsyncSession, typ: str, object_id: UUID) -> None:
    if typ == "observation":
        await owned_observation(db, context.organization.id, object_id)
    elif typ == "task":
        await owned_task(db, context.organization.id, object_id)
    else:
        raise DomainError("NOT_FOUND", "Вложение не найдено", 404)


def media_view(media: Media) -> dict:
    return dict(id=str(media.id), owner_type=media.owner_type, owner_id=str(media.owner_id),
                mime=media.mime, size_bytes=media.size_bytes,
                created_at=media.created_at.isoformat())


@router.get("/media/{owner_type}/{owner_id}")
async def list_media(
    owner_type: str, owner_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    await require_owner(context, db, owner_type, owner_id)
    items = (await db.scalars(select(Media).where(
        Media.org_id == context.organization.id, Media.owner_type == owner_type,
        Media.owner_id == owner_id,
    ).order_by(Media.created_at))).all()
    return [media_view(item) for item in items]


@router.post("/media/{owner_type}/{owner_id}", status_code=201)
async def upload_media(
    owner_type: str, owner_id: UUID,
    file: UploadFile = File(),
    client_media_id: UUID = Form(),
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    assert_owner(context)
    await require_owner(context, db, owner_type, owner_id)
    existing = await db.scalar(select(Media).where(
        Media.org_id == context.organization.id,
        Media.client_media_id == client_media_id,
    ))
    if existing:
        if existing.owner_type != owner_type or existing.owner_id != owner_id:
            raise DomainError("CONFLICT", "ID фото уже используется для другого объекта", 409)
        return media_view(existing)
    count = await db.scalar(select(func.count()).select_from(Media).where(
        Media.org_id == context.organization.id, Media.owner_type == owner_type,
        Media.owner_id == owner_id,
    ))
    if (count or 0) >= 10:
        raise DomainError("MEDIA_LIMIT", "Не более 10 фото на запись", 422)
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise DomainError("UNSUPPORTED_MEDIA", "Поддерживаются JPEG, PNG и WebP", 422)
    raw = await file.read(MAX_INPUT_BYTES + 1)
    encoded = await run_in_threadpool(compress_photo, raw)
    media_id = uuid7()
    key = f"{context.organization.id}/{owner_type}/{owner_id}/{media_id}.jpg"
    try:
        await run_in_threadpool(store().write, key, encoded)
    except Exception as exc:
        raise DomainError("MEDIA_STORAGE_UNAVAILABLE", "Хранилище фотографий недоступно", 503) from exc
    item = Media(id=media_id, org_id=context.organization.id, owner_type=owner_type,
                 owner_id=owner_id, uploaded_by=context.user.id, client_media_id=client_media_id,
                 storage_key=key, mime="image/jpeg", size_bytes=len(encoded))
    db.add(item)
    await db.commit()
    return media_view(item)


@router.get("/media/content/{media_id}")
async def get_media_content(
    media_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    item = await db.scalar(select(Media).where(
        Media.id == media_id, Media.org_id == context.organization.id,
    ))
    if item is None:
        raise DomainError("NOT_FOUND", "Вложение не найдено", 404)
    await require_owner(context, db, item.owner_type, item.owner_id)
    try:
        content = await run_in_threadpool(store().read, item.storage_key)
    except Exception as exc:
        raise DomainError("MEDIA_STORAGE_UNAVAILABLE", "Файл недоступен", 503) from exc
    return Response(content=content, media_type="image/jpeg", headers={
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
    })
