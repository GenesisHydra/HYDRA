"""
Video Recorder - Grabación de sesiones de navegador para HYDRA Browser.

Permite grabar video de la ejecución completa para depuración,
auditoría y entrenamiento de modelos.
"""

import asyncio
import logging
import shutil
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from playwright.async_api import BrowserContext, Page

logger = logging.getLogger(__name__)


@dataclass
class RecordingConfig:
    """Configuración de grabación."""
    enabled: bool = True
    video_dir: Path = Path("recordings")
    video_size: Dict[str, int] = field(default_factory=lambda: {"width": 1920, "height": 1080})
    fps: int = 30
    max_duration_seconds: int = 3600  # 1 hora max
    keep_on_success: bool = False  # Solo guardar si falla
    include_audio: bool = False
    codec: str = "vp8"  # vp8, h264


@dataclass
class RecordingMetadata:
    """Metadatos de una grabación."""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0
    video_path: Optional[Path] = None
    video_size_bytes: int = 0
    context_config: Dict[str, Any] = field(default_factory=dict)
    pages_visited: List[str] = field(default_factory=list)
    actions_count: int = 0
    errors_count: int = 0
    status: str = "recording"  # recording, completed, failed, discarded


class VideoRecorder:
    """
    Grabador de video para sesiones de navegador.

    Características:
    - Grabación automática al crear contexto
    - Metadatos completos (URLs, acciones, errores)
    - Limpieza automática de grabaciones exitosas (configurable)
    - Compresión opcional post-grabación
    - Integración con BrowserPool
    """

    def __init__(self, config: Optional[RecordingConfig] = None):
        self.config = config or RecordingConfig()
        self._recordings: Dict[str, RecordingMetadata] = {}
        self._current_context: Optional[BrowserContext] = None
        self._current_page: Optional[Page] = None
        self._recording_task: Optional[asyncio.Task] = None

        if self.config.enabled:
            self.config.video_dir.mkdir(parents=True, exist_ok=True)

    @asynccontextmanager
    async def record_session(
        self,
        context: BrowserContext,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Context manager para grabar una sesión completa.

        Uso:
            async with recorder.record_session(context) as rec:
                page = await context.new_page()
                await page.goto("https://example.com")
                # ... acciones ...
            # Al salir, se finaliza la grabación
        """
        session_id = session_id or f"rec_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{id(context)}"
        meta = RecordingMetadata(
            session_id=session_id,
            start_time=datetime.utcnow(),
            context_config=metadata or {},
        )
        self._recordings[session_id] = meta
        self._current_context = context

        # Configurar video en el contexto
        if self.config.enabled:
            await self._start_recording(context, session_id)

        try:
            yield self
        except Exception as e:
            meta.errors_count += 1
            meta.status = "failed"
            logger.error(f"Error durante grabación {session_id}: {e}")
            raise
        finally:
            await self._stop_recording(session_id)

    async def _start_recording(self, context: BrowserContext, session_id: str) -> None:
        """Inicia la grabación de video."""
        video_dir = self.config.video_dir / session_id
        video_dir.mkdir(parents=True, exist_ok=True)

        # Playwright graba video automáticamente si el contexto se creó con record_video_dir
        # Aquí asumimos que el contexto ya fue creado con esa opción
        # Si no, no podemos iniciarlo retroactivamente
        logger.info(f"Grabación iniciada: {session_id}")

    async def _stop_recording(self, session_id: str) -> None:
        """Detiene la grabación y procesa el video."""
        meta = self._recordings.get(session_id)
        if not meta:
            return

        meta.end_time = datetime.utcnow()
        meta.duration_seconds = (meta.end_time - meta.start_time).total_seconds()

        # Buscar archivo de video generado por Playwright
        video_dir = self.config.video_dir / session_id
        video_files = list(video_dir.glob("*.webm"))

        if video_files:
            video_path = video_files[0]
            meta.video_path = video_path
            meta.video_size_bytes = video_path.stat().st_size

            # Renombrar a nombre final
            final_path = self.config.video_dir / f"{session_id}.webm"
            if final_path.exists():
                final_path.unlink()
            video_path.rename(final_path)
            meta.video_path = final_path

            # Limpiar directorio temporal
            shutil.rmtree(video_dir, ignore_errors=True)

            logger.info(f"Grabación completada: {session_id} ({meta.video_size_bytes} bytes, {meta.duration_seconds:.1f}s)")
        else:
            logger.warning(f"No se encontró archivo de video para {session_id}")

        # Decidir si mantener o descartar
        if meta.status == "completed" and not self.config.keep_on_success:
            await self.discard(session_id)
        else:
            meta.status = "completed"

    async def discard(self, session_id: str) -> bool:
        """Descarta una grabación (elimina archivo)."""
        meta = self._recordings.pop(session_id, None)
        if meta and meta.video_path and meta.video_path.exists():
            meta.video_path.unlink()
            logger.info(f"Grabación descartada: {session_id}")
            return True
        return False

    def mark_action(self, session_id: str, action: str, url: Optional[str] = None) -> None:
        """Registra una acción en la metadata."""
        meta = self._recordings.get(session_id)
        if meta:
            meta.actions_count += 1
            if url:
                meta.pages_visited.append(url)

    def mark_error(self, session_id: str) -> None:
        """Registra un error."""
        meta = self._recordings.get(session_id)
        if meta:
            meta.errors_count += 1

    def get_metadata(self, session_id: str) -> Optional[RecordingMetadata]:
        """Obtiene metadata de una grabación."""
        return self._recordings.get(session_id)

    def list_recordings(self) -> Dict[str, RecordingMetadata]:
        """Lista todas las grabaciones."""
        return dict(self._recordings)

    async def compress_video(
        self,
        session_id: str,
        crf: int = 28,
        preset: str = "medium",
    ) -> bool:
        """
        Comprime video usando ffmpeg (requiere ffmpeg instalado).

        Returns:
            True si compresión exitosa
        """
        meta = self._recordings.get(session_id)
        if not meta or not meta.video_path or not meta.video_path.exists():
            return False

        try:
            import subprocess
            output_path = meta.video_path.with_suffix(".mp4")
            cmd = [
                "ffmpeg", "-y",
                "-i", str(meta.video_path),
                "-c:v", "libx264",
                "-crf", str(crf),
                "-preset", preset,
                "-movflags", "+faststart",
                str(output_path),
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

            if output_path.exists():
                original_size = meta.video_size_bytes
                compressed_size = output_path.stat().st_size
                meta.video_path.unlink()
                meta.video_path = output_path
                meta.video_size_bytes = compressed_size
                logger.info(f"Video comprimido: {session_id} {original_size} -> {compressed_size} bytes "
                            f"({100 * compressed_size / original_size:.1f}%)")
                return True
        except Exception as e:
            logger.error(f"Error comprimiendo video {session_id}: {e}")
        return False

    def get_total_size(self) -> int:
        """Tamaño total de grabaciones en bytes."""
        return sum(m.video_size_bytes for m in self._recordings.values())

    def cleanup_old(self, max_age_days: int = 7, max_total_gb: float = 5.0) -> int:
        """Limpia grabaciones antiguas o si excede tamaño máximo."""
        import time
        now = time.time()
        max_age_seconds = max_age_days * 86400
        max_bytes = max_total_gb * 1024 * 1024 * 1024

        removed = 0
        total_size = self.get_total_size()

        # Primero por edad
        for session_id, meta in list(self._recordings.items()):
            age = now - meta.start_time.timestamp()
            if age > max_age_seconds:
                self.discard(session_id)
                removed += 1
                total_size -= meta.video_size_bytes

        # Luego por tamaño total (más antiguos primero)
        sorted_by_age = sorted(
            self._recordings.items(),
            key=lambda x: x[1].start_time
        )
        for session_id, meta in sorted_by_age:
            if total_size <= max_bytes:
                break
            self.discard(session_id)
            removed += 1
            total_size -= meta.video_size_bytes

        return removed