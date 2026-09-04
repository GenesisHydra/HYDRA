"""
HYDRA Vault Exceptions
"""
class VaultError(Exception):
    """Base exception for vault errors."""
    pass

class VaultEncryptionError(VaultError):
    """Raised when encryption or decryption fails."""
    pass

class VaultAccessError(VaultError):
    """Raised when access to a secret is denied."""
    pass

class VaultNotFoundError(VaultError):
    """Raised when a secret is not found in the vault."""
    pass

