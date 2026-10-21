import base64
import os
from typing import Optional
from cryptography.fernet import Fernet
from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


class TokenEncryptor:
    """Handles symmetric encryption of OAuth tokens and secrets at rest."""

    def __init__(self, key: Optional[str] = None):
        raw_key = key or settings.ENCRYPTION_KEY
        try:
            # Ensure key is valid Fernet 32-byte url-safe base64
            self.cipher = Fernet(raw_key.encode("utf-8") if isinstance(raw_key, str) else raw_key)
        except Exception as e:
            logger.warning(f"Invalid ENCRYPTION_KEY provided ({e}), generating a fallback ephemeral key.")
            self.cipher = Fernet(Fernet.generate_key())

    def encrypt(self, plain_text: str) -> str:
        """Encrypts plaintext string and returns URL-safe base64 ciphertext."""
        if not plain_text:
            return ""
        return self.cipher.encrypt(plain_text.encode("utf-8")).decode("utf-8")

    def decrypt(self, cipher_text: str) -> str:
        """Decrypts ciphertext and returns original plaintext."""
        if not cipher_text:
            return ""
        try:
            return self.cipher.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to decrypt secret: {e}")
            raise ValueError("Decryption failed. Invalid key or corrupted ciphertext.")


encryptor = TokenEncryptor()
