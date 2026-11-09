"""
CloudSage User Session & Refresh Token Rotation Service.
Tracks active sessions, validates JTI against revocation tables,
and prevents token reuse after logout or suspension.
"""

from datetime import datetime, timedelta, timezone
import hashlib
from typing import Optional, Tuple
from uuid import UUID
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.enums import SessionStatus
from backend.app.models.security import UserSession
from backend.app.models.user import User
from backend.app.security.permissions import get_permissions_for_roles
from backend.app.security.token_service import TokenService


def _hash_token(token: str) -> str:
    """Computes SHA-256 hash of refresh token for safe database indexing."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class SessionService:
    """Manages active user sessions, token rotation, and instant session revocation."""

    @classmethod
    def create_session(
        cls,
        db: Session,
        user: User,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[UserSession, str, str]:
        """
        Creates an active user session in the database and returns:
        (session_record, access_token, refresh_token)
        """
        now = datetime.now(timezone.utc)
        session_id = uuid.uuid4()
        access_jti = str(uuid.uuid4())
        refresh_jti = str(uuid.uuid4())

        # Determine user permissions
        user_roles = [user.role]
        permissions = get_permissions_for_roles(user_roles)

        # Generate tokens
        access_token = TokenService.create_access_token(
            user_id=str(user.id),
            email=user.email,
            tenant_id=str(user.tenant_id) if user.tenant_id else None,
            role=user.role,
            roles=user_roles,
            permissions=permissions,
            session_id=str(session_id),
            jti=access_jti,
        )

        refresh_token = TokenService.create_refresh_token(
            user_id=str(user.id),
            session_id=str(session_id),
            jti=refresh_jti,
        )

        expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        session_record = UserSession(
            id=session_id,
            user_id=user.id,
            token_jti=access_jti,
            refresh_token_hash=_hash_token(refresh_token),
            client_ip=client_ip,
            user_agent=user_agent[:512] if user_agent else None,
            status=SessionStatus.ACTIVE.value,
            created_at=now,
            last_activity_at=now,
            expires_at=expires_at,
        )
        db.add(session_record)
        db.commit()
        db.refresh(session_record)

        return session_record, access_token, refresh_token

    @classmethod
    def refresh_session(
        cls,
        db: Session,
        refresh_token: str,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Rotates refresh token and issues a new access token.
        Enforces single-use refresh token rotation to prevent replay attacks.
        """
        try:
            payload = TokenService.decode_token(refresh_token)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid or expired refresh token: {str(exc)}",
            )

        if payload.get("token_type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token provided is not a valid refresh token",
            )

        session_id_str = payload.get("session_id")
        user_id_str = payload.get("sub")
        if not session_id_str or not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Malformed token claims",
            )

        token_hash = _hash_token(refresh_token)
        session = (
            db.query(UserSession)
            .filter(
                UserSession.id == UUID(session_id_str),
                UserSession.refresh_token_hash == token_hash,
            )
            .first()
        )

        now = datetime.now(timezone.utc)
        if not session or session.status != SessionStatus.ACTIVE.value:
            # Token reuse detected or session already revoked!
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has been revoked or expired.",
            )

        sess_exp = (
            session.expires_at.replace(tzinfo=timezone.utc)
            if session.expires_at.tzinfo is None
            else session.expires_at
        )
        if sess_exp < now:
            session.status = SessionStatus.EXPIRED.value
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has expired. Please authenticate again.",
            )

        user = db.query(User).filter(User.id == UUID(user_id_str)).first()
        if not user or not user.is_active or user.is_locked:
            session.status = SessionStatus.REVOKED.value
            session.revoked_at = now
            session.revoked_by = "system:account_disabled"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated or locked.",
            )

        # Issue new rotated tokens
        new_access_jti = str(uuid.uuid4())
        new_refresh_jti = str(uuid.uuid4())
        user_roles = [user.role]
        permissions = get_permissions_for_roles(user_roles)

        new_access_token = TokenService.create_access_token(
            user_id=str(user.id),
            email=user.email,
            tenant_id=str(user.tenant_id) if user.tenant_id else None,
            role=user.role,
            roles=user_roles,
            permissions=permissions,
            session_id=str(session.id),
            jti=new_access_jti,
        )

        new_refresh_token = TokenService.create_refresh_token(
            user_id=str(user.id),
            session_id=str(session.id),
            jti=new_refresh_jti,
        )

        # Update session with rotated refresh hash and access JTI
        session.token_jti = new_access_jti
        session.refresh_token_hash = _hash_token(new_refresh_token)
        session.last_activity_at = now
        if client_ip:
            session.client_ip = client_ip
        if user_agent:
            session.user_agent = user_agent[:512]
        db.commit()

        return new_access_token, new_refresh_token

    @classmethod
    def revoke_session(
        cls,
        db: Session,
        session_id: UUID,
        actor: str = "user:logout",
    ) -> bool:
        """Revokes an active session immediately."""
        session = db.query(UserSession).filter(UserSession.id == session_id).first()
        if not session:
            return False

        now = datetime.now(timezone.utc)
        session.status = SessionStatus.REVOKED.value
        session.revoked_at = now
        session.revoked_by = actor
        db.commit()
        return True

    @classmethod
    def revoke_all_user_sessions(
        cls,
        db: Session,
        user_id: UUID,
        actor: str = "admin:security_revocation",
    ) -> int:
        """Revokes all active sessions for a target user (e.g. password reset or compromise)."""
        now = datetime.now(timezone.utc)
        active_sessions = (
            db.query(UserSession)
            .filter(
                UserSession.user_id == user_id,
                UserSession.status == SessionStatus.ACTIVE.value,
            )
            .all()
        )
        count = len(active_sessions)
        for s in active_sessions:
            s.status = SessionStatus.REVOKED.value
            s.revoked_at = now
            s.revoked_by = actor
        db.commit()
        return count

    @classmethod
    def is_session_active(
        cls,
        db: Session,
        session_id: UUID,
    ) -> bool:
        """Checks if a session is currently active and unexpired."""
        session = db.query(UserSession).filter(UserSession.id == session_id).first()
        if not session or session.status != SessionStatus.ACTIVE.value:
            return False

        now = datetime.now(timezone.utc)
        exp = session.expires_at.replace(tzinfo=timezone.utc) if session.expires_at.tzinfo is None else session.expires_at
        if exp < now:
            session.status = SessionStatus.EXPIRED.value
            db.commit()
            return False

        return True
