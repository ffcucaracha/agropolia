from __future__ import annotations

from ipaddress import ip_address

from fastapi import APIRouter, Cookie, Depends, Header, Request, Response
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from agropolia.config import Settings, get_settings
from agropolia.db import get_db
from agropolia.errors import DomainError
from agropolia.integrations.email import DevelopmentEmailOtpProvider, SmtpEmailOtpProvider

from .dependencies import AuthContext, get_auth_context
from .otp import OtpService, RedisAttemptLimiter, RedisOtpStore, RedisResendLimiter
from .schemas import LogoutRequest, OtpRequest, OtpRequestResult, OtpVerifyRequest, OtpVerifyResult, RefreshRequest, RegisterRequest, TokenPair
from .service import AuthService
from .tokens import TokenService

router = APIRouter(prefix="/auth", tags=["auth"])
REFRESH_COOKIE = "agropolia_refresh"


def _settings() -> Settings:
    return get_settings()


def _token_service(settings: Settings = Depends(_settings)) -> TokenService:
    return TokenService(settings)


def _auth_service(settings: Settings = Depends(_settings), tokens: TokenService = Depends(_token_service)) -> AuthService:
    return AuthService(settings, tokens)


def _otp_service(request: Request, settings: Settings = Depends(_settings)) -> OtpService:
    redis_client: Redis = request.app.state.redis
    provider = (
        DevelopmentEmailOtpProvider()
        if settings.email_delivery_mode == "dev"
        else SmtpEmailOtpProvider(settings)
    )
    return OtpService(
        settings=settings,
        store=RedisOtpStore(redis_client),
        limiter=RedisAttemptLimiter(redis_client, settings.otp_attempt_limit, settings.otp_attempt_window_seconds),
        resend_limiter=RedisResendLimiter(redis_client),
        provider=provider,
    )


def _client_ip(request: Request) -> str | None:
    host = request.client.host if request.client else None
    if not host:
        return None
    try:
        return str(ip_address(host))
    except ValueError:
        return None


def _is_web(platform: str | None) -> bool:
    return (platform or "web").lower() == "web"


def _set_refresh_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=settings.refresh_ttl_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/api/v1/auth",
    )


def _client_tokens(response: Response, tokens: TokenPair, platform: str | None, settings: Settings) -> TokenPair:
    if _is_web(platform):
        if tokens.refresh_token:
            _set_refresh_cookie(response, tokens.refresh_token, settings)
        return tokens.model_copy(update={"refresh_token": None})
    return tokens


def _ensure_method_enabled(method: str, settings: Settings) -> None:
    if method not in settings.enabled_auth_methods:
        raise DomainError("AUTH_METHOD_DISABLED", "Способ входа отключён", 400)


@router.post("/otp/request", response_model=OtpRequestResult)
async def request_otp(
    payload: OtpRequest,
    otp: OtpService = Depends(_otp_service),
    settings: Settings = Depends(_settings),
) -> OtpRequestResult:
    _ensure_method_enabled(payload.method, settings)
    if payload.method != "email":
        raise DomainError("AUTH_METHOD_DISABLED", "В I-0 доступна только авторизация по email", 400)
    code = await otp.request(payload.method, payload.identifier, payload.device_id, payload.purpose)
    return OtpRequestResult(
        expires_in=settings.otp_ttl_seconds,
        resend_available_in=settings.otp_resend_cooldown_seconds,
        dev_code=code if settings.email_delivery_mode == "dev" else None,
    )


@router.post("/otp/verify", response_model=OtpVerifyResult)
async def verify_otp(
    payload: OtpVerifyRequest,
    request: Request,
    response: Response,
    x_client_platform: str | None = Header(default="web", alias="X-Client-Platform"),
    otp: OtpService = Depends(_otp_service),
    auth: AuthService = Depends(_auth_service),
    tokens: TokenService = Depends(_token_service),
    settings: Settings = Depends(_settings),
    db: AsyncSession = Depends(get_db),
) -> OtpVerifyResult:
    _ensure_method_enabled(payload.method, settings)
    await otp.verify(payload.method, payload.identifier, payload.device_id, payload.purpose, payload.code)
    if payload.purpose == "register":
        return OtpVerifyResult(
            registration_token=tokens.create_registration(payload.method, payload.identifier, payload.device_id)
        )
    pair = await auth.login(
        db,
        payload.method,
        payload.identifier,
        payload.device_id,
        _client_ip(request),
    )
    return OtpVerifyResult(tokens=_client_tokens(response, pair, x_client_platform, settings))


@router.post("/register", response_model=TokenPair)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    x_client_platform: str | None = Header(default="web", alias="X-Client-Platform"),
    auth: AuthService = Depends(_auth_service),
    tokens: TokenService = Depends(_token_service),
    settings: Settings = Depends(_settings),
    db: AsyncSession = Depends(get_db),
) -> TokenPair:
    registration = tokens.decode_registration(payload.registration_token)
    pair = await auth.register(db, payload, registration, _client_ip(request))
    return _client_tokens(response, pair, x_client_platform, settings)


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    payload: RefreshRequest,
    request: Request,
    response: Response,
    cookie_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
    x_client_platform: str | None = Header(default="web", alias="X-Client-Platform"),
    auth: AuthService = Depends(_auth_service),
    settings: Settings = Depends(_settings),
    db: AsyncSession = Depends(get_db),
) -> TokenPair:
    token = cookie_token if _is_web(x_client_platform) else payload.refresh_token
    if not token:
        raise DomainError("INVALID_REFRESH", "Refresh token отсутствует", 401)
    pair = await auth.refresh(db, token, payload.device_id, _client_ip(request))
    return _client_tokens(response, pair, x_client_platform, settings)


@router.post("/logout", status_code=204)
async def logout(
    payload: LogoutRequest,
    request: Request,
    response: Response,
    context: AuthContext = Depends(get_auth_context),
    auth: AuthService = Depends(_auth_service),
    db: AsyncSession = Depends(get_db),
) -> None:
    await auth.logout(db, context.session.id, context.user.id, _client_ip(request))
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth")
