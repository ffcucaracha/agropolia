from __future__ import annotations

from fastapi import APIRouter, Header

from agropolia.config import get_settings
from agropolia.shared.versioning import evaluate_version

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/client-version")
async def client_version(x_client_platform: str = Header(alias="X-Client-Platform"), x_client_version: str = Header(alias="X-Client-Version")):
    return evaluate_version(x_client_platform.lower(), x_client_version, get_settings())
