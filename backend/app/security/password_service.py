"""
CloudSage Password Hashing & Complexity Validation Service.
Implements secure bcrypt hashing with salt and OWASP complexity rules.
"""

import re
from typing import Optional, Tuple
import bcrypt

from backend.app.core.config import settings


class PasswordService:
    """Manages password hashing, verification, and enterprise complexity enforcement."""

    @classmethod
    def hash_password(cls, password: str) -> str:
        """Generates a secure salted bcrypt hash for a plaintext password."""
        # bcrypt standard accepts up to 72 bytes
        encoded = password.encode("utf-8")[:72]
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(encoded, salt)
        return hashed.decode("utf-8")

    @classmethod
    def verify_password(cls, plain_password: str, hashed_password: str) -> bool:
        """Verifies a plaintext password against a stored bcrypt hash."""
        if not plain_password or not hashed_password:
            return False
        try:
            encoded_plain = plain_password.encode("utf-8")[:72]
            encoded_hash = hashed_password.encode("utf-8")
            return bcrypt.checkpw(encoded_plain, encoded_hash)
        except Exception:
            return False

    @classmethod
    def validate_password_strength(cls, password: str) -> Tuple[bool, Optional[str]]:
        """
        Enforces enterprise password complexity:
        - Minimum length (configurable, default 12)
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one decimal digit
        - At least one special symbol (!@#$%^&*()-_=+...)
        """
        min_length = settings.PASSWORD_MIN_LENGTH
        if len(password) < min_length:
            return False, f"Password must be at least {min_length} characters long."

        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter."

        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter."

        if not re.search(r"\d", password):
            return False, "Password must contain at least one numerical digit."

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>\-_=+\[\]\\/~`';]", password):
            return False, "Password must contain at least one special character."

        return True, None
