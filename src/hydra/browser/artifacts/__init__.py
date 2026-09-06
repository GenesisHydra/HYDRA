"""
Artifact Store - Almacén de evidencias y artefactos para HYDRA Browser.

Persistencia estructurada de:
- Screenshots
- Videos
- Logs de ejecución
- Reportes de validación
- Scripts Pine/código fuente
- Errores de compilación
- Metadatos de sesión
"""

import hashlib
import json
import logging
import shutil
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class Artifact:
    """Un artefacto individual."""
    artifact_id: str
    artifact_type: str  # screenshot, video, log, report, script, error, html, har
    path: Path
    size_bytes: int
    created_at: datetime
    session_id: str
    module: str  # tradingview, gmail, generic, etc.
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    checksum: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "path": str(self.path),
            "size_bytes": self.size_bytes,
            "created_at": self.created_at.isoformat(),
            "session_id": self.session_id,
            "module": self.module,
            "tags": self.tags,
            "metadata": self.metadata,
            "checksum": self.checksum,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Artifact":
        return cls(
            artifact_id=data["artifact_id"],
            artifact_type=data["artifact_type"],
            path=Path(data["path"]),
            size_bytes=data["size_bytes"],
            created_at=datetime.fromisoformat(data["created_at"]),
            session_id=data["session_id"],
            module=data["module"],
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            checksum=data.get("checksum", ""),
        )


@dataclass
class SessionArtifacts:
    """Contenedor de artefactos de una sesión."""
    session_id: str
    module: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    artifacts: List[Artifact] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "module": self.module,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "artifacts": [a.to_dict() for a in self.artifacts],
            "summary": self.summary,
        }


class ArtifactStore:
    """
    Almacén de artefactos con índice y consultas.

    Organización en disco:
        artifacts/
        ├── tradingview/
        │   ├── 2026-09-04/
        │   │   ├── session_abc123/
        │   │   │   ├── session.json
        │   │   │   ├── screenshot_chart.png
        │   │   │   ├── video.webm
        │   │   │   ├── compilation_errors.json
        │   │   │   └── validation_report.html
        │   │   └── index.json
        │   └── index.json
        └── index.json
    """

    def __init__(
        self,
        root_dir: Path,
        max_size_gb: float = 10.0,
        compress_old: bool = True,
    ):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = int(max_size_gb * 1024 * 1024 * 1024)
        self.compress_old = compress_old

        self._index: Dict[str, SessionArtifacts] = {}
        self._load_index()

    def _load_index(self) -> None:
        """Carga índice principal."""
        index_path = self.root_dir / "index.json"
        if index_path.exists():
            try:
                data = json.loads(index_path.read_text())
                for module, module_data in data.get("modules", {}).items():
                    for session_id, session_data in module_data.get("sessions", {}).items():
                        artifacts = [
                            Artifact.from_dict(a) for a in session_data.get("artifacts", [])
                        ]
                        session = SessionArtifacts(
                            session_id=session_data["session_id"],
                            module=module,
                            started_at=datetime.fromisoformat(session_data["started_at"]),
                            ended_at=datetime.fromisoformat(session_data["ended_at"]) if session_data.get("ended_at") else None,
                            artifacts=artifacts,
                            summary=session_data.get("summary", {}),
                        )
                        self._index[session_id] = session
            except Exception as e:
                logger.warning(f"Error cargando índice: {e}")

    def _save_index(self) -> None:
        """Guarda índice principal."""
        modules: Dict[str, Dict[str, Any]] = {}
        for session in self._index.values():
            if session.module not in modules:
                modules[session.module] = {"sessions": {}}
            modules[session.module]["sessions"][session.session_id] = session.to_dict()

        index_path = self.root_dir / "index.json"
        index_path.write_text(json.dumps({"modules": modules}, indent=2))

    def _session_dir(self, module: str, session_id: str) -> Path:
        """Directorio de una sesión."""
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        return self.root_dir / module / date_str / session_id

    def _compute_checksum(self, path: Path) -> str:
        """Calcula SHA256 de un archivo."""
        hasher = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    @asynccontextmanager
    async def session(self, module: str, session_id: Optional[str] = None) -> SessionArtifacts:
        """Context manager para una sesión de artefactos."""
        session_id = session_id or f"sess_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{hashlib.md5(module.encode()).hexdigest()[:6]}"
        session_dir = self._session_dir(module, session_id)
        session_dir.mkdir(parents=True, exist_ok=True)

        session = SessionArtifacts(
            session_id=session_id,
            module=module,
            started_at=datetime.utcnow(),
        )
        self._index[session_id] = session

        try:
            yield session
        except Exception as e:
            session.summary["error"] = str(e)
            raise
        finally:
            session.ended_at = datetime.utcnow()
            session.summary["duration_seconds"] = (session.ended_at - session.started_at).total_seconds()
            session.summary["artifact_count"] = len(session.artifacts)
            session.summary["total_size_bytes"] = sum(a.size_bytes for a in session.artifacts)

            # Guardar session.json
            session_file = session_dir / "session.json"
            session_file.write_text(json.dumps(session.to_dict(), indent=2))

            # Actualizar índice
            self._save_index()

            # Verificar límite de tamaño
            await self._enforce_size_limit()

    async def add_artifact(
        self,
        session: SessionArtifacts,
        artifact_type: str,
        content: Union[bytes, str, Path],
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        filename: Optional[str] = None,
    ) -> Artifact:
        """Añade un artefacto a la sesión."""
        session_dir = self._session_dir(session.module, session.session_id)
        session_dir.mkdir(parents=True, exist_ok=True)

        # Determinar nombre de archivo
        if filename is None:
            ext_map = {
                "screenshot": ".png",
                "video": ".webm",
                "log": ".log",
                "report": ".json",
                "script": ".pine",
                "error": ".json",
                "html": ".html",
                "har": ".har",
            }
            ext = ext_map.get(artifact_type, ".bin")
            timestamp = datetime.utcnow().strftime("%H%M%S")
            filename = f"{artifact_type}_{timestamp}{ext}"

        file_path = session_dir / filename

        # Escribir contenido
        if isinstance(content, Path):
            shutil.copy2(content, file_path)
        elif isinstance(content, bytes):
            file_path.write_bytes(content)
        elif isinstance(content, str):
            file_path.write_text(content, encoding="utf-8")
        else:
            raise TypeError(f"Tipo de contenido no soportado: {type(content)}")

        # Crear artifact
        size = file_path.stat().st_size
        checksum = self._compute_checksum(file_path)

        artifact = Artifact(
            artifact_id=f"art_{hashlib.md5(f"{session.session_id}{filename}".encode()).hexdigest()[:8]}",
            artifact_type=artifact_type,
            path=file_path,
            size_bytes=size,
            created_at=datetime.utcnow(),
            session_id=session.session_id,
            module=session.module,
            tags=tags or [],
            metadata=metadata or {},
            checksum=checksum,
        )

        session.artifacts.append(artifact)
        logger.debug(f"Artefacto añadido: {artifact.artifact_id} ({artifact_type}, {size} bytes)")
        return artifact

    async def add_screenshot(
        self,
        session: SessionArtifacts,
        page,
        name: str = "screenshot",
        full_page: bool = True,
        selector: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Artifact:
        """Captura y guarda screenshot."""
        if selector:
            # Screenshot de elemento específico
            # Requiere selector válido
            locator = page.locator(selector)
            content = await locator.screenshot(type="png")
        else:
            content = await page.screenshot(full_page=full_page, type="png")

        return await self.add_artifact(
            session,
            "screenshot",
            content,
            tags=["screenshot", name],
            metadata=metadata or {},
            filename=f"{name}.png",
        )

    async def add_video(
        self,
        session: SessionArtifacts,
        video_path: Path,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Artifact:
        """Registra video existente."""
        return await self.add_artifact(
            session,
            "video",
            video_path,
            tags=["video"],
            metadata=metadata or {},
        )

    async def add_script(
        self,
        session: SessionArtifacts,
        script_content: str,
        script_name: str = "script",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Artifact:
        """Guarda script (Pine, JS, etc.)."""
        return await self.add_artifact(
            session,
            "script",
            script_content,
            tags=["script", script_name],
            metadata=metadata or {},
            filename=f"{script_name}.pine",
        )

    async def add_error_report(
        self,
        session: SessionArtifacts,
        errors: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Artifact:
        """Guarda reporte de errores estructurado."""
        return await self.add_artifact(
            session,
            "error",
            {"errors": errors, "count": len(errors)},
            tags=["error", "compilation"],
            metadata=metadata or {},
            filename="compilation_errors.json",
        )

    async def add_validation_report(
        self,
        session: SessionArtifacts,
        report: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Artifact:
        """Guarda reporte de validación (JSON + HTML)."""
        # JSON
        json_art = await self.add_artifact(
            session,
            "report",
            report,
            tags=["report", "validation", "json"],
            metadata=metadata or {},
            filename="validation_report.json",
        )

        # HTML (versión legible)
        html = self._generate_html_report(report)
        html_art = await self.add_artifact(
            session,
            "report",
            html,
            tags=["report", "validation", "html"],
            metadata=metadata or {},
            filename="validation_report.html",
        )

        return json_art

    def _generate_html_report(self, report: Dict[str, Any]) -> str:
        """Genera reporte HTML legible."""
        status = report.get("status", "UNKNOWN")
        status_color = {
            "SUCCESS": "#28a745",
            "COMPILATION_ERROR": "#dc3545",
            "RUNTIME_ERROR": "#fd7e14",
            "TIMEOUT": "#6c757d",
        }.get(status, "#6c757d")

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Validation Report - {report.get('script', 'unknown')}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 40px; }}
        .header {{ border-bottom: 2px solid #eee; padding-bottom: 20px; margin-bottom: 30px; }}
        .status {{ display: inline-block; padding: 8px 16px; border-radius: 4px; color: white; font-weight: bold; }}
        .section {{ margin-bottom: 30px; }}
        .section h2 {{ color: #333; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
        pre {{ background: #f8f9fa; padding: 15px; border-radius: 4px; overflow-x: auto; }}
        .error {{ color: #dc3545; }}
        .warning {{ color: #ffc107; }}
        .success {{ color: #28a745; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #eee; }}
        img {{ max-width: 100%; border: 1px solid #ddd; border-radius: 4px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Validation Report</h1>
        <p><strong>Script:</strong> {report.get('script', 'unknown')}</p>
        <p><strong>Timestamp:</strong> {report.get('timestamp', 'unknown')}</p>
        <span class="status" style="background: {status_color};">{status}</span>
    </div>

    <div class="section">
        <h2>Compilation</h2>
        <p><strong>Success:</strong> {report.get('compilation', {}).get('success', False)}</p>
        <p><strong>Errors:</strong> {len(report.get('compilation', {}).get('errors', []))}</p>
        <p><strong>Warnings:</strong> {len(report.get('compilation', {}).get('warnings', []))}</p>
"""

        errors = report.get('compilation', {}).get('errors', [])
        if errors:
            html += "<h3>Errors</h3><table><tr><th>Line</th><th>Message</th><th>Code</th></tr>"
            for err in errors:
                html += f"<tr class='error'><td>{err.get('line', '?')}</td><td>{err.get('message', '')}</td><td>{err.get('code', '')}</td></tr>"
            html += "</table>"

        html += f"""
    </div>

    <div class="section">
        <h2>Metrics</h2>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Total Duration</td><td>{report.get('metrics', {}).get('total_duration_ms', 0)} ms</td></tr>
            <tr><td>Login Duration</td><td>{report.get('metrics', {}).get('login_duration_ms', 0)} ms</td></tr>
            <tr><td>Compilation Duration</td><td>{report.get('metrics', {}).get('compilation_duration_ms', 0)} ms</td></tr>
        </table>
    </div>

    <div class="section">
        <h2>Screenshots</h2>
"""

        for key, path in report.get('screenshots', {}).items():
            html += f'<p><strong>{key}:</strong> <img src="{path}" alt="{key}"></p>'

        html += """
    </div>
</body>
</html>"""
        return html

    async def _enforce_size_limit(self) -> None:
        """Aplica límite de tamaño total eliminando sesiones antiguas."""
        total_size = sum(
            a.size_bytes for s in self._index.values() for a in s.artifacts
        )

        if total_size <= self.max_size_bytes:
            return

        # Ordenar por fecha (más antiguas primero)
        sorted_sessions = sorted(
            self._index.values(),
            key=lambda s: s.started_at
        )

        for session in sorted_sessions:
            if total_size <= self.max_size_bytes:
                break

            # Eliminar archivos
            for artifact in session.artifacts:
                if artifact.path.exists():
                    artifact.path.unlink()
                    total_size -= artifact.size_bytes

            # Eliminar directorio de sesión
            session_dir = self._session_dir(session.module, session.session_id)
            if session_dir.exists():
                shutil.rmtree(session_dir, ignore_errors=True)

            # Eliminar del índice
            del self._index[session.session_id]
            logger.info(f"Sesión eliminada por límite de tamaño: {session.session_id}")

        self._save_index()

    def get_session(self, session_id: str) -> Optional[SessionArtifacts]:
        """Obtiene una sesión por ID."""
        return self._index.get(session_id)

    def query(
        self,
        module: Optional[str] = None,
        artifact_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Artifact]:
        """Consulta artefactos con filtros."""
        results = []
        for session in self._index.values():
            if module and session.module != module:
                continue
            for artifact in session.artifacts:
                if artifact_type and artifact.artifact_type != artifact_type:
                    continue
                if tags and not any(t in artifact.tags for t in tags):
                    continue
                if since and artifact.created_at < since:
                    continue
                results.append(artifact)
                if len(results) >= limit:
                    break
            if len(results) >= limit:
                break
        return results

    def get_stats(self) -> Dict[str, Any]:
        """Estadísticas del almacén."""
        total_artifacts = sum(len(s.artifacts) for s in self._index.values())
        total_size = sum(a.size_bytes for s in self._index.values() for a in s.artifacts)
        modules = {}
        for session in self._index.values():
            if session.module not in modules:
                modules[session.module] = {"sessions": 0, "artifacts": 0, "size_bytes": 0}
            modules[session.module]["sessions"] += 1
            modules[session.module]["artifacts"] += len(session.artifacts)
            modules[session.module]["size_bytes"] += sum(a.size_bytes for a in session.artifacts)

        return {
            "total_sessions": len(self._index),
            "total_artifacts": total_artifacts,
            "total_size_bytes": total_size,
            "total_size_gb": round(total_size / (1024**3), 2),
            "max_size_gb": round(self.max_size_bytes / (1024**3), 2),
            "modules": modules,
        }