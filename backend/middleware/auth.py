"""JWT RS256 authentication middleware for NEXUS-NODE.

All /api/v1/* routes (except /health and /stream SSE) require a valid Bearer token.
Tokens are signed with RS256 and expire in jwt_expire_minutes (default 1 hour).
"""

from __future__ import annotations

import structlog
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from config import get_settings

logger: structlog.BoundLogger = structlog.get_logger(__name__)

_bearer = HTTPBearer(auto_error=True)


class TokenPayload(BaseModel):
    """Validated claims from a decoded JWT."""

    sub: str          # user / service identifier
    exp: int          # unix timestamp
    iat: int          # issued-at
    role: str = "user"


def create_access_token(sub: str, role: str = "user") -> str:
    """Sign and return a new RS256 JWT for the given subject.

    Args:
        sub: Subject identifier (user id, service name, etc.).
        role: Role claim embedded in the token.

    Returns:
        Signed JWT string.
    """
    settings = get_settings()
    now = int(datetime.now(timezone.utc).timestamp())
    payload = {
        "sub": sub,
        "role": role,
        "iat": now,
        "exp": now + settings.jwt_expire_minutes * 60,
    }
    key_str = settings.jwt_private_key.get_secret_value()
    if not key_str or "BEGIN" not in key_str or "PRIVATE KEY" not in key_str:
        logger.error("missing_jwt_private_key")
        raise RuntimeError("JWT_PRIVATE_KEY is not properly configured (expected PEM format)")
    
    return jwt.encode(
        payload,
        key_str.replace("\\n", "\n"),
        algorithm=settings.jwt_algorithm,
    )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> TokenPayload:
    """FastAPI dependency — validates the Bearer token and returns its payload.

    Args:
        credentials: Injected by FastAPI from the Authorization header.

    Returns:
        Decoded and validated TokenPayload.

    Raises:
        HTTPException 401 if the token is missing, expired, or invalid.
    """
    settings = get_settings()
    token = credentials.credentials

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.jwt_public_key.replace("\\n", "\n"),
            algorithms=[settings.jwt_algorithm],
        )
        parsed = TokenPayload(**payload)
    except (JWTError, Exception) as exc:
        logger.warning("jwt_validation_failed", error=str(exc))
        raise credentials_exception from exc

    return parsed


# Convenience type alias for injection in route handlers
CurrentUser = Annotated[TokenPayload, Depends(get_current_user)]
