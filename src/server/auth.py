import hashlib
import os
import hmac

# Simple PBKDF2 password hashing utilities for prototype
DEFAULT_ITERATIONS = 100_000


def hash_password(password: str, iterations: int = DEFAULT_ITERATIONS) -> str:
    """Return a string containing method, iterations, salt and hash hex.

    Format: pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>
    """
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${dk.hex()}"


def verify_password(stored: str, candidate: str) -> bool:
    try:
        method, it_s, salt_hex, hash_hex = stored.split("$")
        iterations = int(it_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        dk = hashlib.pbkdf2_hmac("sha256", candidate.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False
