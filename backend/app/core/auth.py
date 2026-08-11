import hashlib
import hmac
import secrets

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

_pwd_context = PasswordHash((Argon2Hasher(),))

# Pre-computed dummy hash to prevent timing attacks when email does not exist
DUMMY_HASH: str = "$argon2id$v=19$m=65536,t=3,p=4$c29tZXNhbHQ$dHVtbXlnaGFzaGZvcnRpbWluZ3ByZXZlbnRpb24"


def hash_password(plain_password: str) -> str:
    """Hash password using Argon2id."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify password using Argon2id."""
    try:
        return _pwd_context.verify(plain_password, password_hash)
    except Exception:
        return False


def generate_session_token() -> str:
    """Generate CSPRNG session token with 256 bits of entropy."""
    return secrets.token_urlsafe(32)


def hash_session_token(token: str, secret: str) -> str:
    """Derive session token storage hash via HMAC-SHA-256."""
    return hmac.new(secret.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()
