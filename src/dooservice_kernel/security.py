from __future__ import annotations

import base64
import secrets

import bcrypt
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
import nacl.encoding
import nacl.hash
import nacl.secret

from .constants import OTP_DIGITS


class PasswordHasher:
    def hash(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify(self, password: str, password_hash: str) -> bool:
        return bcrypt.checkpw(password.encode(), password_hash.encode())


class CookieSigner:
    """Signs and verifies opaque cookie values (session ids, OAuth state)."""

    def __init__(self, secret: str) -> None:
        self.serializer = URLSafeTimedSerializer(secret)

    def sign(self, value: str) -> str:
        return self.serializer.dumps(value)

    def unsign(self, signed_value: str, max_age_seconds: int) -> str | None:
        try:
            return self.serializer.loads(signed_value, max_age=max_age_seconds)
        except (BadSignature, SignatureExpired):
            return None


class OtpGenerator:
    def generate(self) -> str:
        return "".join(secrets.choice("0123456789") for digit in range(OTP_DIGITS))


class TokenGenerator:
    def generate(self) -> str:
        return secrets.token_urlsafe(32)


class SecretCipher:
    """Encrypts credentials that have to be stored and used again later.

    A GitHub access token is not a password: it cannot be hashed, because we have to
    replay it to GitHub. So it is encrypted, and the threat this answers is a copy of
    the database — a backup, a stolen file, a support dump. Those carry the tables and
    not the configuration, which is where the key stays.

    The key is derived from the session secret rather than configured separately.
    Both would live in the same file anyway, so a second one buys no isolation and
    costs a way to lose it. The derivation is domain-separated, so the key that
    encrypts tokens is not the value that signs cookies even though one comes from the
    other. Rotating the session secret orphans stored tokens; it also logs everybody
    out, and a customer reconnects GitHub in two clicks.

    Ciphertext is tagged `v1:` so a value that has not been encrypted yet is
    recognisable and returned as it is. That is what lets the column hold both while a
    migration works through it.
    """

    PREFIX = "v1:"

    def __init__(self, secret: str, purpose: bytes) -> None:
        """`purpose` goes into the key: two ciphers of one secret with different purposes
        cannot read each other, and changing it makes everything sealed unreadable."""
        self.box = nacl.secret.SecretBox(
            nacl.hash.blake2b(
                secret.encode(),
                digest_size=nacl.secret.SecretBox.KEY_SIZE,
                person=purpose,
                encoder=nacl.encoding.RawEncoder,
            )
        )

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            return plaintext
        sealed = self.box.encrypt(plaintext.encode())
        return self.PREFIX + base64.urlsafe_b64encode(sealed).decode()

    def decrypt(self, value: str) -> str:
        """Anything without the tag is returned untouched — it predates encryption.

        A tagged value that will not open is a real problem, not a legacy one: the key
        changed. Raising beats handing back something that is not the token, which
        would reach GitHub and come back as a permission error nobody could explain.
        """
        if not value or not value.startswith(self.PREFIX):
            return value
        sealed = base64.urlsafe_b64decode(value[len(self.PREFIX) :])
        return self.box.decrypt(sealed).decode()
