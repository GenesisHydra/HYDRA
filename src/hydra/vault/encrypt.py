"""
HYDRA Vault Encryption Utilities
"""
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from .exceptions import VaultEncryptionError

def generate_key() -> bytes:
    """
    Generate a new encryption key.
    
    Returns:
        A random key suitable for Fernet.
    """
    return Fernet.generate_key()

def derive_key_from_password(password: str, salt: bytes = None) -> bytes:
    """
    Derive a key from a password using PBKDF2.
    
    Args:
        password: The password to derive the key from.
        salt: Optional salt. If not provided, a new salt will be generated.
    
    Returns:
        A tuple (key, salt) where key is the derived key and salt is the salt used.
    """
    if salt is None:
        salt = os.urandom(16)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key, salt

def encrypt_data(data: bytes, key: bytes) -> bytes:
    """
    Encrypt data using Fernet.
    
    Args:
        data: The data to encrypt.
        key: The encryption key.
    
    Returns:
        Encrypted data.
    """
    try:
        f = Fernet(key)
        return f.encrypt(data)
    except Exception as e:
        raise VaultEncryptionError(f"Encryption failed: {e}")

def decrypt_data(encrypted_data: bytes, key: bytes) -> bytes:
    """
    Decrypt data using Fernet.
    
    Args:
        encrypted_data: The encrypted data.
        key: The encryption key.
    
    Returns:
        Decrypted data.
    """
    try:
        f = Fernet(key)
        return f.decrypt(encrypted_data)
    except Exception as e:
        raise VaultEncryptionError(f"Decryption failed: {e}")

