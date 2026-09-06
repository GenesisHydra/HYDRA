"""
Session Manager - Gestión de perfiles persistentes cifrados por servicio.

Cada servicio (TradingView, Gmail, YouTube, etc.) tiene su propio perfil
que almacena cookies, localStorage, sessionStorage, permisos, preferencias
y cache necesario. Todo cifrado en disco.
"""

import base64
import json
import logging
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from playwright.async_api import BrowserContext, Page

logger = logging.getLogger(__name__)


@dataclass
class EncryptedProfile:
    """Perfil de navegador cifrado para un servicio específico."""
    service_name: str
    cookies: List[Dict[str, Any]] = field(default_factory=list)
    local_storage: Dict[str, str] = field(default_factory=dict)
    session_storage: Dict[str, str] = field(default_factory=dict)
    permissions: Dict[str, str] = field(default_factory=dict)
    preferences: Dict[str, Any] = field(default_factory=dict)
    cache_metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_name": self.service_name,
            "cookies": self.cookies,
            "local_storage": self.local_storage,
            "session_storage": self.session_storage,
            "permissions": self.permissions,
            "preferences": self.preferences,
            "cache_metadata": self.cache_metadata,
            "created_at": self.created_at,
            "updated_at": datetime.utcnow().isoformat(),
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EncryptedProfile":
        return cls(
            service_name=data["service_name"],
            cookies=data.get("cookies", []),
            local_storage=data.get("local_storage", {}),
            session_storage=data.get("session_storage", {}),
            permissions=data.get("permissions", {}),
            preferences=data.get("preferences", {}),
            cache_metadata=data.get("cache_metadata", {}),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            updated_at=data.get("updated_at", datetime.utcnow().isoformat()),
            version=data.get("version", 1),
        )


class SessionManager:
    """
    Gestor de sesiones persistentes cifradas por servicio.

    Características:
    - Un perfil por servicio (tradingview, gmail, youtube, etc.)
    - Cifrado AES-256 (Fernet) con clave derivada de master key
    - Persistencia automática en disco
    - Sincronización bidireccional: browser <-> disco
    - Migración de versiones
    - Backup automático antes de escribir
    """

    def __init__(
        self,
        profiles_dir: Path,
        master_key: Optional[bytes] = None,
        master_key_env: str = "HYDRA_BROWSER_MASTER_KEY",
    ):
        self.profiles_dir = Path(profiles_dir)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

        # Derivar clave de cifrado
        if master_key:
            self._key = master_key
        else:
            env_key = os.environ.get(master_key_env)
            if not env_key:
                raise ValueError(
                    f"Master key no proporcionada. Configura {master_key_env} "
                    "o pasa master_key al constructor."
                )
            self._key = self._derive_key(env_key.encode())

        self._fernet = Fernet(base64.urlsafe_b64encode(self._key[:32]))
        self._profiles: Dict[str, EncryptedProfile] = {}
        self._dirty: Dict[str, bool] = {}

    def _derive_key(self, password: bytes) -> bytes:
        """Deriva clave de 32 bytes usando PBKDF2."""
        salt = b"hydra-browser-salt-v1"  # Salt fijo para determinismo
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(password)

    def _profile_path(self, service_name: str) -> Path:
        """Ruta del archivo de perfil cifrado."""
        safe_name = service_name.lower().replace(" ", "_").replace(".", "_")
        return self.profiles_dir / f"{safe_name}.profile.enc"

    def _backup_path(self, service_name: str) -> Path:
        """Ruta del backup del perfil."""
        safe_name = service_name.lower().replace(" ", "_").replace(".", "_")
        return self.profiles_dir / f"{safe_name}.profile.enc.bak"

    def _encrypt(self, data: Dict[str, Any]) -> bytes:
        """Cifra un diccionario."""
        json_data = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        return self._fernet.encrypt(json_data.encode("utf-8"))

    def _decrypt(self, encrypted: bytes) -> Dict[str, Any]:
        """Descifra a diccionario."""
        decrypted = self._fernet.decrypt(encrypted)
        return json.loads(decrypted.decode("utf-8"))

    def load_profile(self, service_name: str) -> EncryptedProfile:
        """Carga un perfil desde disco (o crea uno nuevo)."""
        if service_name in self._profiles:
            return self._profiles[service_name]

        path = self._profile_path(service_name)
        if path.exists():
            try:
                encrypted = path.read_bytes()
                data = self._decrypt(encrypted)
                profile = EncryptedProfile.from_dict(data)
                logger.info(f"Perfil cargado: {service_name}")
            except Exception as e:
                logger.warning(f"Error cargando perfil {service_name}, creando nuevo: {e}")
                profile = EncryptedProfile(service_name=service_name)
        else:
            profile = EncryptedProfile(service_name=service_name)
            logger.info(f"Perfil nuevo creado: {service_name}")

        self._profiles[service_name] = profile
        self._dirty[service_name] = False
        return profile

    def save_profile(self, service_name: str, force: bool = False) -> bool:
        """Guarda un perfil en disco (solo si hay cambios o force=True)."""
        if service_name not in self._profiles:
            logger.warning(f"Intento de guardar perfil inexistente: {service_name}")
            return False

        if not self._dirty.get(service_name, False) and not force:
            return False

        profile = self._profiles[service_name]
        profile.updated_at = datetime.utcnow().isoformat()
        path = self._profile_path(service_name)

        # Backup antes de escribir
        if path.exists():
            shutil.copy2(path, self._backup_path(service_name))

        try:
            encrypted = self._encrypt(profile.to_dict())
            path.write_bytes(encrypted)
            self._dirty[service_name] = False
            logger.debug(f"Perfil guardado: {service_name}")
            return True
        except Exception as e:
            logger.error(f"Error guardando perfil {service_name}: {e}")
            # Restaurar backup si existe
            backup = self._backup_path(service_name)
            if backup.exists():
                shutil.copy2(backup, path)
            return False

    def save_all(self, force: bool = False) -> int:
        """Guarda todos los perfiles modificados."""
        count = 0
        for service_name in self._profiles:
            if self.save_profile(service_name, force=force):
                count += 1
        return count

    async def sync_from_browser(self, service_name: str, context: BrowserContext) -> None:
        """Sincroniza el estado del navegador al perfil (cookies, storage, etc.)."""
        profile = self.load_profile(service_name)

        # Cookies
        cookies = await context.cookies()
        profile.cookies = [
            {
                "name": c["name"],
                "value": c["value"],
                "domain": c["domain"],
                "path": c["path"],
                "expires": c.get("expires", -1),
                "httpOnly": c.get("httpOnly", False),
                "secure": c.get("secure", False),
                "sameSite": c.get("sameSite", "Lax"),
            }
            for c in cookies
        ]

        # localStorage y sessionStorage via evaluate
        try:
            local_storage = await context.evaluate("() => JSON.stringify(localStorage)")
            profile.local_storage = json.loads(local_storage) if local_storage else {}
        except Exception:
            pass

        try:
            session_storage = await context.evaluate("() => JSON.stringify(sessionStorage)")
            profile.session_storage = json.loads(session_storage) if session_storage else {}
        except Exception:
            pass

        self._dirty[service_name] = True

    async def sync_to_browser(self, service_name: str, context: BrowserContext) -> None:
        """Aplica el perfil al navegador (cookies, storage, etc.)."""
        profile = self.load_profile(service_name)

        # Cookies
        if profile.cookies:
            await context.add_cookies(profile.cookies)

        # localStorage
        if profile.local_storage:
            await context.add_init_script(f"""
                Object.entries({json.dumps(profile.local_storage)}).forEach(([k, v]) => {{
                    localStorage.setItem(k, v);
                }});
            """)

        # sessionStorage (se aplica en la primera página)
        if profile.session_storage:
            await context.add_init_script(f"""
                Object.entries({json.dumps(profile.session_storage)}).forEach(([k, v]) => {{
                    sessionStorage.setItem(k, v);
                }});
            """)

    async def apply_to_page(self, service_name: str, page: Page) -> None:
        """Aplica sessionStorage a una página específica (después de navegación)."""
        profile = self.load_profile(service_name)
        if profile.session_storage:
            await page.evaluate(f"""
                Object.entries({json.dumps(profile.session_storage)}).forEach(([k, v]) => {{
                    sessionStorage.setItem(k, v);
                }});
            """)

    async def clear_session_storage(self, service_name: str, context: BrowserContext) -> None:
        """Limpia sessionStorage del perfil y del navegador."""
        profile = self.load_profile(service_name)
        profile.session_storage = {}
        await context.evaluate("() => sessionStorage.clear()")
        self._dirty[service_name] = True

    def get_profile(self, service_name: str) -> Optional[EncryptedProfile]:
        """Obtiene un perfil cargado (None si no existe)."""
        return self._profiles.get(service_name)

    def list_profiles(self) -> List[str]:
        """Lista nombres de perfiles cargados."""
        return list(self._profiles.keys())

    def delete_profile(self, service_name: str) -> bool:
        """Elimina un perfil (memoria y disco)."""
        if service_name in self._profiles:
            del self._profiles[service_name]
            self._dirty.pop(service_name, None)

        path = self._profile_path(service_name)
        backup = self._backup_path(service_name)
        removed = False

        for p in (path, backup):
            if p.exists():
                p.unlink()
                removed = True

        if removed:
            logger.info(f"Perfil eliminado: {service_name}")
        return removed

    def export_profile(self, service_name: str, export_path: Path) -> bool:
        """Exporta un perfil descifrado (para backup/migración)."""
        profile = self.load_profile(service_name)
        try:
            export_path.write_text(
                json.dumps(profile.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            return True
        except Exception as e:
            logger.error(f"Error exportando perfil {service_name}: {e}")
            return False

    def import_profile(self, service_name: str, import_path: Path) -> bool:
        """Importa un perfil desde archivo JSON descifrado."""
        try:
            data = json.loads(import_path.read_text(encoding="utf-8"))
            profile = EncryptedProfile.from_dict(data)
            profile.service_name = service_name
            self._profiles[service_name] = profile
            self._dirty[service_name] = True
            self.save_profile(service_name, force=True)
            logger.info(f"Perfil importado: {service_name}")
            return True
        except Exception as e:
            logger.error(f"Error importando perfil {service_name}: {e}")
            return False