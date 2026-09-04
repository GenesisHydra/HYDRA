"""
HYDRA Vault Core Module
Handles secure storage and retrieval of secrets.
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VaultError(Exception):
    """Base exception for vault errors."""
    pass

class Vault:
    """
    A secure vault for storing secrets.
    """
    
    def __init__(self, vault_dir: str = None):
        """
        Initialize the vault.
        
        Args:
            vault_dir: Directory to store vault files. Defaults to config/vault/
        """
        if vault_dir is None:
            # Default to config/vault relative to the project root
            # We assume the project root is two levels up from this file? 
            # Actually, we can get the current file's directory and go up.
            # But for simplicity, we'll use an environment variable or a fixed path.
            # Let's use the current working directory's config/vault.
            vault_dir = os.path.join(os.getcwd(), 'config', 'vault')
        
        self.vault_dir = vault_dir
        self.secrets_file = os.path.join(vault_dir, 'secrets.enc')
        self.key_file = os.path.join(vault_dir, 'master.key')
        self.log_file = os.path.join(vault_dir, 'access.log')
        
        # Ensure vault directory exists
        os.makedirs(self.vault_dir, exist_ok=True)
        
        # Initialize encryption key
        self._init_key()
        
        # Initialize access logging
        self._init_logging()
    
    def _init_key(self):
        """Initialize or load the encryption key."""
        if os.path.exists(self.key_file):
            with open(self.key_file, 'rb') as f:
                key = f.read()
        else:
            # Generate a new key
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
            # Restrict permissions to owner only
            os.chmod(self.key_file, 0o600)
        
        self.fernet = Fernet(key)
    
    def _init_logging(self):
        """Initialize access logging to a file."""
        # We'll use a simple file log for now.
        # In production, we might want to use a logging handler.
        pass
    
    def _log_access(self, operation: str, key: str, success: bool, details: str = None):
        """Log an access operation."""
        timestamp = datetime.utcnow().isoformat()
        log_entry = {
            'timestamp': timestamp,
            'operation': operation,
            'key': key,
            'success': success,
            'details': details
        }
        # Write to log file as JSON lines
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        # Also log to the logger
        if success:
            logger.info(f"Vault {operation} for key '{key}': {details}")
        else:
            logger.warning(f"Vault {operation} failed for key '{key}': {details}")
    
    def _load_secrets(self) -> Dict[str, Any]:
        """Load and decrypt the secrets from the secrets file."""
        if not os.path.exists(self.secrets_file):
            return {}
        
        try:
            with open(self.secrets_file, 'rb') as f:
                encrypted_data = f.read()
            decrypted_data = self.fernet.decrypt(encrypted_data)
            secrets = json.loads(decrypted_data.decode('utf-8'))
            return secrets
        except Exception as e:
            self._log_access('load_secrets', 'N/A', False, str(e))
            raise VaultError(f"Failed to load secrets: {e}")
    
    def _save_secrets(self, secrets: Dict[str, Any]):
        """Encrypt and save the secrets to the secrets file."""
        try:
            data = json.dumps(secrets).encode('utf-8')
            encrypted_data = self.fernet.encrypt(data)
            with open(self.secrets_file, 'wb') as f:
                f.write(encrypted_data)
            # Restrict permissions to owner only
            os.chmod(self.secrets_file, 0o600)
        except Exception as e:
            self._log_access('save_secrets', 'N/A', False, str(e))
            raise VaultError(f"Failed to save secrets: {e}")
    
    def set_secret(self, key: str, value: Any, metadata: Dict[str, Any] = None) -> bool:
        """
        Set a secret in the vault.
        
        Args:
            key: The identifier for the secret.
            value: The secret value (must be JSON serializable).
            metadata: Optional metadata about the secret (e.g., type, owner, expiration).
        
        Returns:
            True if successful.
        """
        try:
            secrets = self._load_secrets()
            # Store the secret with metadata and timestamp
            secrets[key] = {
                'value': value,
                'metadata': metadata or {},
                'updated_at': datetime.utcnow().isoformat(),
                'version': secrets.get(key, {}).get('version', 0) + 1
            }
            self._save_secrets(secrets)
            self._log_access('set_secret', key, True, f"Version {secrets[key]['version']}")
            return True
        except Exception as e:
            self._log_access('set_secret', key, False, str(e))
            return False
    
    def get_secret(self, key: str) -> Optional[Any]:
        """
        Get a secret from the vault.
        
        Args:
            key: The identifier for the secret.
        
        Returns:
            The secret value if found, None otherwise.
        """
        try:
            secrets = self._load_secrets()
            if key in secrets:
                secret_data = secrets[key]
                self._log_access('get_secret', key, True, f"Version {secret_data['version']}")
                return secret_data['value']
            else:
                self._log_access('get_secret', key, False, "Key not found")
                return None
        except Exception as e:
            self._log_access('get_secret', key, False, str(e))
            return None
    
    def delete_secret(self, key: str) -> bool:
        """
        Delete a secret from the vault.
        
        Args:
            key: The identifier for the secret.
        
        Returns:
            True if successful.
        """
        try:
            secrets = self._load_secrets()
            if key in secrets:
                del secrets[key]
                self._save_secrets(secrets)
                self._log_access('delete_secret', key, True, "Secret deleted")
                return True
            else:
                self._log_access('delete_secret', key, False, "Key not found")
                return False
        except Exception as e:
            self._log_access('delete_secret', key, False, str(e))
            return False
    
    def list_secrets(self) -> List[str]:
        """
        List all secret keys in the vault.
        
        Returns:
            A list of secret keys.
        """
        try:
            secrets = self._load_secrets()
            keys = list(secrets.keys())
            self._log_access('list_secrets', 'N/A', True, f"Found {len(keys)} secrets")
            return keys
        except Exception as e:
            self._log_access('list_secrets', 'N/A', False, str(e))
            return []
    
    def get_secret_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a secret.
        
        Args:
            key: The identifier for the secret.
        
        Returns:
            Metadata dictionary if found, None otherwise.
        """
        try:
            secrets = self._load_secrets()
            if key in secrets:
                metadata = secrets[key].get('metadata', {})
                # Add some vault metadata
                metadata.update({
                    'updated_at': secrets[key]['updated_at'],
                    'version': secrets[key]['version']
                })
                self._log_access('get_metadata', key, True, f"Version {secrets[key]['version']}")
                return metadata
            else:
                self._log_access('get_metadata', key, False, "Key not found")
                return None
        except Exception as e:
            self._log_access('get_metadata', key, False, str(e))
            return None
    
    def rotate_secret(self, key: str, new_value: Any) -> bool:
        """
        Rotate a secret by updating its value.
        
        Args:
            key: The identifier for the secret.
            new_value: The new secret value.
        
        Returns:
            True if successful.
        """
        return self.set_secret(key, new_value)

# For backward compatibility, we can also provide a function to get the vault instance.
_vault_instance = None

def get_vault() -> Vault:
    """Get a singleton instance of the Vault."""
    global _vault_instance
    if _vault_instance is None:
        _vault_instance = Vault()
    return _vault_instance

