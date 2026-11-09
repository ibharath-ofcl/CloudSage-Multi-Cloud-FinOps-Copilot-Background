"""
CloudSage Cryptographic JWT Token Service.
Issues and validates cryptographically signed JWT access tokens and refresh tokens
with expiration enforcement, issuer/audience verification, and JTI tracking.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set
import uuid

from jose import JWTError, jwt

from backend.app.core.config import settings


class TokenService:
    """Cryptographic JWT token generation and claims validation."""

    @classmethod
    def create_access_token(
        cls,
        user_id: str,
        email: str,
        tenant_id: Optional[str] = None,
        role: str = "VIEWER",
        roles: Optional[List[str]] = None,
        permissions: Optional[Set[str]] = None,
        session_id: Optional[str] = None,
        jti: Optional[str] = None,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Issues an HMAC-SHA256 cryptographically signed access token."""
        now = datetime.now(timezone.utc)
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        token_jti = jti or str(uuid.uuid4())
        user_roles = roles or [role]
        perm_list = list(permissions) if permissions else []

        claims: Dict[str, Any] = {
            "sub": str(user_id),
            "email": email,
            "tenant_id": str(tenant_id) if tenant_id else None,
            "role": role,
            "roles": user_roles,
            "permissions": perm_list,
            "session_id": str(session_id) if session_id else None,
            "jti": token_jti,
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "token_type": "access",
        }

        encoded_jwt = jwt.encode(
            claims,
            settings.SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        return encoded_jwt

    @classmethod
    def create_refresh_token(
        cls,
        user_id: str,
        session_id: Optional[str] = None,
        jti: Optional[str] = None,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Issues a cryptographically signed refresh token."""
        now = datetime.now(timezone.utc)
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        token_jti = jti or str(uuid.uuid4())

        claims: Dict[str, Any] = {
            "sub": str(user_id),
            "session_id": str(session_id) if session_id else None,
            "jti": token_jti,
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "token_type": "refresh",
        }

        encoded_jwt = jwt.encode(
            claims,
            settings.SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        return encoded_jwt

    @classmethod
    def decode_token(
        cls,
        token: str,
        verify_exp: bool = True,
    ) -> Dict[str, Any]:
        """
        Decodes and cryptographically verifies token signature, issuer, audience, and expiry.
        Raises JWTError on invalid or tampered tokens.
        """
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
            options={"verify_exp": verify_exp},
        )
        return payload

    @classmethod
    def verify_access_token(cls, token: str) -> Dict[str, Any]:
        """
        Cryptographically verifies an access token.
        Raises HTTPException(401) on failure, signature mismatch, or expired token.
        """
        from fastapi import HTTPException, status
        try:
            payload = cls.decode_token(token, verify_exp=True)
            if payload.get("token_type") != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token is not an access token.",
                )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired.",
            )
        except JWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Cryptographic token verification failed: {str(exc)}",
            )
