from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hmac
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from core.config import BACKEND_DIR, load_environment

load_environment(BACKEND_DIR / ".env")

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)
ALGORITHM = "HS256"
TOKEN_MINUTES = 60


class LoginRequest(BaseModel):
    username: str
    password: str


def _secret() -> str:
    secret = os.getenv("JWT_SECRET")
    if not secret or secret in {"any_long_random_string", "change_me"}:
        raise RuntimeError("JWT_SECRET must be configured with a strong random value")
    return secret


def create_token(username: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_MINUTES)
    return jwt.encode({"sub": username, "exp": expires}, _secret(), algorithm=ALGORITHM)


def current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        payload = jwt.decode(credentials.credentials, _secret(), algorithms=[ALGORITHM])
        username = payload.get("sub")
    except (JWTError, RuntimeError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
    return str(username)


@router.post("/login")
def login(request: LoginRequest) -> dict[str, str]:
    expected_user = os.getenv("DASHBOARD_USER")
    expected_password = os.getenv("DASHBOARD_PASSWORD")
    if not expected_user or not expected_password:
        raise HTTPException(status_code=503, detail="Dashboard credentials are not configured")
    if not hmac.compare_digest(request.username, expected_user) or not hmac.compare_digest(
        request.password, expected_password
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    try:
        token = create_token(request.username)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"access_token": token, "token_type": "bearer"}