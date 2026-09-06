# -------------------------------------------------------------------------
# Web Connector para HYDRA
# Gestiona la web https://genesishydra.github.io/HYDRA/ desde el VPS.
# Recupera la URL del Vault (company/website) y permite operarla remotamente.
# Sigue el patron de TelegramConnector: vault + servicio + health_check.
# -------------------------------------------------------------------------
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from hydra.vault import get_vault

logger = logging.getLogger(__name__)

# Clave del Vault donde se almacena la URL de la web
WEB_URL_VAULT_KEY = "company/website"
DEFAULT_WEB_URL = "https://genesishydra.github.io/HYDRA/"
DEFAULT_SITE_DIR = "/home/genesis/opt/genesis/HYDRA"
DEFAULT_DEPLOY_BRANCH = "gh-pages"


# -------------------------------------------------------------------------
# WebService - envoltura ligera sobre requests para operaciones de la web.
# -------------------------------------------------------------------------
class WebService:
    """Wrapper de operaciones HTTP para gestionar la web de HYDRA.

    Proporciona metodos de alto nivel para consultar, descargar y verificar
    el contenido de la web sin exponer detalles de implementacion.
    """

    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "HYDRA-WebConnector/1.0 (PythonRequests)"
        })

    def get_page(self, path: str = "/") -> Dict[str, Any]:
        """Obtiene el contenido HTML de una pagina.

        Args:
            path: Ruta relativa desde la base_url (ej: "/index.html").

        Returns:
            dict con "status_code", "content", "headers", "ok".
        """
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            resp = self._session.get(url, timeout=self.timeout)
            return {
                "ok": True,
                "status_code": resp.status_code,
                "content": resp.text,
                "headers": dict(resp.headers),
                "url": resp.url,
            }
        except requests.RequestException as exc:
            logger.error("Error al obtener %s: %s", url, exc)
            return {
                "ok": False,
                "status_code": 0,
                "content": "",
                "headers": {},
                "url": url,
                "error": str(exc),
            }

    def download_file(self, path: str, local_path: str) -> Dict[str, Any]:
        """Descarga un archivo de la web y lo guarda localmente."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            resp = self._session.get(url, timeout=self.timeout, stream=True)
            resp.raise_for_status()
            content = resp.content
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(content)
            sha = hashlib.sha256(content).hexdigest()
            return {
                "ok": True,
                "local_path": local_path,
                "size": len(content),
                "sha256": sha,
            }
        except requests.RequestException as exc:
            logger.error("Error al descargar %s: %s", url, exc)
            return {
                "ok": False,
                "local_path": local_path,
                "size": 0,
                "sha256": "",
                "error": str(exc),
            }

    def check_health(self) -> Dict[str, Any]:
        """Verifica que la web este accesible."""
        start = time.time()
        try:
            resp = self._session.get(self.base_url, timeout=self.timeout)
            elapsed = (time.time() - start) * 1000
            return {
                "ok": resp.status_code == 200,
                "status_code": resp.status_code,
                "response_time_ms": round(elapsed, 2),
                "url": resp.url,
            }
        except requests.RequestException as exc:
            elapsed = (time.time() - start) * 1000
            return {
                "ok": False,
                "status_code": 0,
                "response_time_ms": round(elapsed, 2),
                "url": self.base_url,
                "error": str(exc),
            }

    def get_sitemap(self) -> Dict[str, Any]:
        """Intenta obtener el sitemap.xml de la web."""
        result = self.get_page("sitemap.xml")
        if not result["ok"]:
            return {"ok": False, "urls": [], "error": "sitemap no disponible"}
        urls = []
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(result["content"])
            for loc in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
                urls.append(loc.text)
        except Exception as exc:
            return {"ok": False, "urls": [], "error": str(exc)}
        return {"ok": True, "urls": urls}

    def get_robots_txt(self) -> Dict[str, Any]:
        """Obtiene el contenido de robots.txt."""
        result = self.get_page("robots.txt")
        return {
            "ok": result["ok"],
            "content": result.get("content", ""),
            "status_code": result.get("status_code", 0),
        }


# -------------------------------------------------------------------------
# WebConnector - clase principal que el resto de HYDRA usara.
# -------------------------------------------------------------------------
class WebConnector:
    """Conector web para HYDRA.

    Responsabilidades:
    * Obtener la URL de la web desde el Vault.
    * Proporcionar metodos de alto nivel para gestionar la web.
    * Validar conectividad y estado de la web.
    """

    def __init__(self, *,
                 vault: Any | None = None,
                 base_url: str | None = None,
                 site_dir: str | None = None,
                 ):
        """Inicializa el conector web.

        Args:
            vault: Instancia de Vault opcional (para testing).
            base_url: URL base de la web (sobrescribe la del Vault).
            site_dir: Directorio local del sitio (para operaciones de build/deploy).
        """
        self._vault = vault or get_vault()
        self._base_url = base_url
        self._site_dir = site_dir or DEFAULT_SITE_DIR
        self._service: Optional[WebService] = None
        self._last_health_check: Optional[float] = None

    def _ensure_service(self) -> WebService:
        """Asegura que exista una instancia de WebService."""
        if self._service is None:
            url = self._base_url or self._vault.get_secret(WEB_URL_VAULT_KEY)
            if not url:
                logger.warning(
                    "URL de web no encontrada en Vault (%s). Usando valor por defecto: %s",
                    WEB_URL_VAULT_KEY, DEFAULT_WEB_URL
                )
                url = DEFAULT_WEB_URL
            self._service = WebService(base_url=url)
        return self._service

    def _get_site_dir(self) -> Path:
        """Devuelve el directorio local del sitio como Path."""
        return Path(self._site_dir)

    def health_check(self) -> Dict[str, Any]:
        """Verifica que la web este accesible."""
        result: Dict[str, Any] = {"valid": False, "message": ""}
        try:
            service = self._ensure_service()
            health = service.check_health()
            if health["ok"]:
                result["valid"] = True
                result["message"] = (
                    f"Webconnector OK. "
                    f"URL: {service.base_url} | "
                    f"Status: {health['status_code']} | "
                    f"Response: {health['response_time_ms']}ms"
                )
                self._service = service
                self._last_health_check = time.time()
            else:
                result["message"] = (
                    f"Web no responde: HTTP {health['status_code']} | "
                    f"Error: {health.get('error', 'desconocido')}"
                )
        except Exception as exc:
            result["message"] = f"Excepcion en health_check: {exc}"
            logger.exception("WebConnector health_check fallo")
        return result

    def get_web_url(self) -> str:
        """Devuelve la URL de la web configurada."""
        service = self._ensure_service()
        return service.base_url

    def get_page(self, path: str = "/") -> Dict[str, Any]:
        """Obtiene el contenido de una pagina."""
        service = self._ensure_service()
        return service.get_page(path)

    def check_local_build(self) -> Dict[str, Any]:
        """Verifica si existe un build local del sitio."""
        site_dir = self._get_site_dir()
        index_path = site_dir / "index.html"
        dist_path = site_dir / "dist"
        site_path = site_dir / "_site"
        build_exists = index_path.exists() or dist_path.exists() or site_path.exists()
        file_count = 0
        if build_exists:
            base = dist_path if dist_path.exists() else (site_path if site_path.exists() else site_dir)
            for root_dir, _, files in os.walk(base):
                file_count += len(files)
        return {
            "ok": build_exists,
            "site_dir": str(site_dir),
            "has_index": index_path.exists(),
            "files_count": file_count,
            "build_dirs": {
                "index": str(index_path),
                "dist": str(dist_path),
                "_site": str(site_path),
            },
        }

    def list_public_files(self) -> List[str]:
        """Lista los archivos publicos del build local."""
        site_dir = self._get_site_dir()
        dist = site_dir / "dist"
        site = site_dir / "_site"
        base = dist if dist.exists() else (site if site.exists() else site_dir)
        public_exts = {".html", ".css", ".js", ".png", ".jpg", ".jpeg", ".svg", ".ico", ".xml", ".txt"}
        files = []
        for root_dir, _, filenames in os.walk(base):
            for fname in filenames:
                if Path(fname).suffix.lower() in public_exts:
                    rel = Path(root_dir).relative_to(base)
                    files.append(str(rel / fname) if str(rel) != "." else fname)
        return sorted(files)

    def sync_to_remote(self) -> Dict[str, Any]:
        """Verifica sincronizacion entre build local y web remota."""
        local = self.check_local_build()
        remote = self.health_check()
        return {
            "ok": local["ok"] and remote["valid"],
            "message": (
                f"Archivos locales: {local['files_count']} | "
                f"Web remota: {'OK' if remote['valid'] else 'ERROR'}"
            ),
            "local_files": local["files_count"],
            "remote_status": remote["valid"],
            "web_url": self.get_web_url(),
        }

    def get_site_info(self) -> Dict[str, Any]:
        """Devuelve informacion general del sitio."""
        return {
            "url": self.get_web_url(),
            "site_dir": str(self._get_site_dir()),
            "last_health_check": (
                self._last_health_check
                if self._last_health_check
                else None
            ),
            "vault_key": WEB_URL_VAULT_KEY,
        }

    def fetch_page_metadata(self, path: str = "/") -> Dict[str, Any]:
        """Extrae metadatos basicos de una pagina (titulo, meta descripcion)."""
        result = self.get_page(path)
        if not result["ok"]:
            return {"ok": False, "title": "", "description": "", "og_image": ""}
        import re
        html = result["content"]
        title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        desc_match = re.search(
            r'<meta\s+(?:name=["\']description["\']\s+content=["\']([^"\']+)["\']|'
            r'content=["\']([^"\']+)["\']\s+name=["\']description["\'])',
            html, re.IGNORECASE
        )
        og_match = re.search(
            r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']',
            html, re.IGNORECASE
        )
        title = title_match.group(1).strip() if title_match else ""
        desc = (desc_match.group(1) or desc_match.group(2) or "").strip() if desc_match else ""
        og_image = og_match.group(1).strip() if og_match else ""
        return {
            "ok": True,
            "title": title,
            "description": desc,
            "og_image": og_image,
            "status_code": result["status_code"],
        }


# -------------------------------------------------------------------------
# Funcion de conveniencia a nivel de modulo.
# -------------------------------------------------------------------------
def health_check() -> Dict[str, Any]:
    """Retorna el estado de salud del conector web.

    Crea una instancia temporal de WebConnector y llama a su metodo
    health_check(). Util para verificaciones rapidas desde CLI o ARGOS.
    """
    from hydra.web.connector import WebConnector
    conn = WebConnector()
    return conn.health_check()
