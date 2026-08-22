from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import settings

ALGORITHM = "HS256"

_bearer_strict = HTTPBearer(auto_error=True)
_bearer_soft = HTTPBearer(auto_error=False)


def create_access_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expires_min),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_strict),
) -> str:
    try:
        payload = jwt.decode(
            credentials.credentials, settings.jwt_secret, algorithms=[ALGORITHM]
        )
        username = payload.get("sub")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный токен"
        )
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный токен"
        )
    return username


def optional_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_soft),
) -> str | None:
    if credentials is None:
        return None
    try:
        payload = jwt.decode(
            credentials.credentials, settings.jwt_secret, algorithms=[ALGORITHM]
        )
        return payload.get("sub")
    except JWTError:
        return None
