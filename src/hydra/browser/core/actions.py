"""
Browser Actions - API de alto nivel para acciones de navegador.

Esta es la interfaz que usan los agentes a través del MCP.
Proporciona acciones semánticas (login, compile_pine, etc.)
en lugar de comandos de bajo nivel de Playwright.
"""

import asyncio
import hashlib
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from playwright.async_api import Download, Page

from hydra.browser.core.browser_pool import BrowserPool
from hydra.browser.core.session_manager import SessionManager
from hydra.browser.artifacts import ArtifactStore
from hydra.browser.vision import VisionAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class ActionResult:
    """Resultado de una acción."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    duration_ms: float = 0
    artifacts: List[str] = field(default_factory=list)


class BrowserActions:
    """
    Acciones de alto nivel para automatización web.

    Abstrae Playwright y proporciona operaciones semánticas
    que los agentes pueden usar directamente.
    """

    def __init__(
        self,
        page: Page,
        browser_pool: BrowserPool,
        session_manager: SessionManager,
        artifact_store: ArtifactStore,
        vision_analyzer: Optional[VisionAnalyzer] = None,
        module_name: str = "generic",
    ):
        self.page = page
        self.browser_pool = browser_pool
        self.session_manager = session_manager
        self.artifact_store = artifact_store
        self.vision_analyzer = vision_analyzer
        self.module_name = module_name
        self._action_count = 0

    # ===== Navegación =====

    async def goto(
        self,
        url: str,
        wait_until: str = "networkidle",
        timeout: float = 30000,
    ) -> ActionResult:
        """Navega a URL."""
        start = datetime.utcnow()
        try:
            await self.page.goto(url, wait_until=wait_until, timeout=timeout)
            return ActionResult(
                success=True,
                data={"url": self.page.url, "title": await self.page.title()},
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    async def go_back(self, wait_until: str = "networkidle") -> ActionResult:
        return await self._nav_action(self.page.go_back, wait_until=wait_until)

    async def go_forward(self, wait_until: str = "networkidle") -> ActionResult:
        return await self._nav_action(self.page.go_forward, wait_until=wait_until)

    async def reload(self, wait_until: str = "networkidle") -> ActionResult:
        return await self._nav_action(self.page.reload, wait_until=wait_until)

    async def _nav_action(self, func, **kwargs) -> ActionResult:
        start = datetime.utcnow()
        try:
            await func(**kwargs)
            return ActionResult(
                success=True,
                data={"url": self.page.url},
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    # ===== Interacción =====

    async def click(
        self,
        selector: str,
        force: bool = False,
        timeout: float = 10000,
    ) -> ActionResult:
        """Click en elemento."""
        return await self._element_action(
            lambda loc: loc.click(force=force, timeout=timeout),
            selector,
        )

    async def double_click(self, selector: str, timeout: float = 10000) -> ActionResult:
        return await self._element_action(lambda loc: loc.dblclick(timeout=timeout), selector)

    async def hover(self, selector: str, timeout: float = 10000) -> ActionResult:
        return await self._element_action(lambda loc: loc.hover(timeout=timeout), selector)

    async def fill(
        self,
        selector: str,
        value: str,
        clear_first: bool = True,
        timeout: float = 10000,
    ) -> ActionResult:
        """Rellena campo."""
        async def _fill(loc):
            if clear_first:
                await loc.clear(timeout=timeout)
            await loc.fill(value, timeout=timeout)
        return await self._element_action(_fill, selector)

    async def press(
        self,
        selector: str,
        key: str,
        modifiers: Optional[List[str]] = None,
        timeout: float = 10000,
    ) -> ActionResult:
        """Presiona tecla."""
        return await self._element_action(
            lambda loc: loc.press(key, modifiers=modifiers, timeout=timeout),
            selector,
        )

    async def select(
        self,
        selector: str,
        value: Union[str, List[str]],
        timeout: float = 10000,
    ) -> ActionResult:
        """Selecciona opción."""
        return await self._element_action(
            lambda loc: loc.select_option(value, timeout=timeout),
            selector,
        )

    async def check(self, selector: str) -> ActionResult:
        return await self._element_action(lambda loc: loc.check(), selector)

    async def uncheck(self, selector: str) -> ActionResult:
        return await self._element_action(lambda loc: loc.uncheck(), selector)

    async def _element_action(self, action_func, selector: str) -> ActionResult:
        start = datetime.utcnow()
        try:
            locator = self.page.locator(selector)
            await action_func(locator)
            self._action_count += 1
            return ActionResult(
                success=True,
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    # ===== Extracción =====

    async def get_text(
        self,
        selector: str,
        timeout: float = 5000,
    ) -> ActionResult:
        """Obtiene texto de elemento."""
        start = datetime.utcnow()
        try:
            locator = self.page.locator(selector)
            await locator.wait_for(state="visible", timeout=timeout)
            text = await locator.text_content(timeout=timeout)
            return ActionResult(
                success=True,
                data={"text": text.strip() if text else ""},
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    async def get_attribute(
        self,
        selector: str,
        attribute: str,
    ) -> ActionResult:
        start = datetime.utcnow()
        try:
            value = await self.page.locator(selector).get_attribute(attribute)
            return ActionResult(
                success=True,
                data={attribute: value},
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    async def get_value(self, selector: str) -> ActionResult:
        start = datetime.utcnow()
        try:
            value = await self.page.locator(selector).input_value()
            return ActionResult(
                success=True,
                data={"value": value},
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    async def is_visible(self, selector: str, timeout: float = 5000) -> bool:
        try:
            await self.page.locator(selector).wait_for(state="visible", timeout=timeout)
            return True
        except Exception:
            return False

    async def extract_table(
        self,
        selector: str,
    ) -> ActionResult:
        """Extrae tabla a lista de dicts."""
        start = datetime.utcnow()
        try:
            rows = await self.page.locator(f"{selector} tr").all()
            if not rows:
                return ActionResult(success=True, data=[])

            # Headers
            headers = []
            header_cells = await rows[0].locator("th").all()
            for h in headers_cells:
                headers.append((await h.text_content() or "").strip())

            # Data
            data = []
            for row in rows[1:]:
                cells = await row.locator("td").all()
                values = [(await c.text_content() or "").strip() for c in cells]
                if len(values) == len(headers):
                    data.append(dict(zip(headers, values)))

            return ActionResult(
                success=True,
                data=data,
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    # ===== Esperas =====

    async def wait_for_selector(
        self,
        selector: str,
        state: str = "visible",
        timeout: float = 10000,
    ) -> ActionResult:
        start = datetime.utcnow()
        try:
            await self.page.locator(selector).wait_for(state=state, timeout=timeout)
            return ActionResult(
                success=True,
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    async def wait_for_url(self, pattern: str, timeout: float = 10000) -> ActionResult:
        start = datetime.utcnow()
        try:
            await self.page.wait_for_url(pattern, timeout=timeout)
            return ActionResult(
                success=True,
                data={"url": self.page.url},
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    async def wait_for_text(
        self,
        text: str,
        selector: str = "body",
        timeout: float = 10000,
    ) -> ActionResult:
        """Espera a que aparezca texto en página."""
        start = datetime.utcnow()
        try:
            locator = self.page.locator(selector)
            await locator.wait_for(state="visible", timeout=timeout)

            import time
            max_wait = timeout / 1000
            start_time = time.time()
            while time.time() - start_time < max_wait:
                content = await locator.text_content()
                if content and text in content:
                    return ActionResult(
                        success=True,
                        data={"found": True},
                        duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
                    )
                await asyncio.sleep(0.1)
            return ActionResult(
                success=True,
                data={"found": False},
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    async def wait_for_download(self, timeout: float = 30000) -> ActionResult:
        start = datetime.utcnow()
        try:
            async with self.page.expect_download(timeout=timeout) as download_info:
                pass  # Trigger externo
            download: Download = await download_info.value
            return ActionResult(
                success=True,
                data={"path": download.path(), "filename": download.suggested_filename},
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    # ===== Capturas =====

    async def screenshot(
        self,
        path: Optional[Union[str, Path]] = None,
        full_page: bool = True,
        selector: Optional[str] = None,
    ) -> ActionResult:
        """Captura screenshot."""
        start = datetime.utcnow()
        try:
            if selector:
                content = await self.page.locator(selector).screenshot(path=path, type="png")
            else:
                content = await self.page.screenshot(path=path, full_page=full_page, type="png")

            artifact_id = None
            if self.artifact_store:
                async with self.artifact_store.session(self.module_name) as session:
                    artifact = await self.artifact_store.add_artifact(
                        session,
                        "screenshot",
                        content if isinstance(content, bytes) else path,
                        tags=["screenshot"],
                        filename=Path(path).name if path else f"screenshot_{datetime.utcnow().strftime('%H%M%S')}.png",
                    )
                    artifact_id = artifact.artifact_id

            return ActionResult(
                success=True,
                data={"path": str(path) if path else "bytes", "artifact_id": artifact_id},
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    # ===== Archivos =====

    async def upload_file(
        self,
        selector: str,
        file_path: Union[str, Path],
    ) -> ActionResult:
        start = datetime.utcnow()
        try:
            await self.page.locator(selector).set_input_files(file_path)
            return ActionResult(
                success=True,
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    async def download_file(
        self,
        trigger_selector: str,
        save_path: Optional[Path] = None,
        timeout: float = 30000,
    ) -> ActionResult:
        start = datetime.utcnow()
        try:
            async with self.page.expect_download(timeout=timeout) as download_info:
                await self.page.locator(trigger_selector).click()
            download = await download_info.value
            if save_path:
                await download.save_as(save_path)
            return ActionResult(
                success=True,
                data={"path": save_path or download.path(), "filename": download.suggested_filename},
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    # ===== JavaScript =====

    async def evaluate(self, script: str, *args) -> ActionResult:
        start = datetime.utcnow()
        try:
            result = await self.page.evaluate(script, *args)
            return ActionResult(
                success=True,
                data=result,
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    # ===== Visión =====

    async def analyze_visual(self) -> ActionResult:
        """Análisis visual completo (OCR + DOM)."""
        if not self.vision_analyzer:
            return ActionResult(success=False, error="VisionAnalyzer no configurado")

        start = datetime.utcnow()
        try:
            analysis = await self.vision_analyzer.analyze(self.page)
            return ActionResult(
                success=True,
                data={
                    "elements_count": len(analysis.combined_elements),
                    "states": analysis.detected_states,
                    "image_hash": analysis.image_hash,
                },
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    async def find_text_visual(self, text: str) -> ActionResult:
        """Busca texto visualmente (OCR + DOM)."""
        if not self.vision_analyzer:
            return ActionResult(success=False, error="VisionAnalyzer no configurado")

        start = datetime.utcnow()
        try:
            matches = await self.vision_analyzer.find_text(self.page, text)
            return ActionResult(
                success=True,
                data={"matches": len(matches), "elements": [{"text": m.text, "bbox": m.bbox} for m in matches]},
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    async def click_by_text(self, text: str) -> ActionResult:
        """Click en elemento encontrado por texto visual."""
        if not self.vision_analyzer:
            return ActionResult(success=False, error="VisionAnalyzer no configurado")

        start = datetime.utcnow()
        try:
            success = await self.vision_analyzer.click_by_text(self.page, text)
            return ActionResult(
                success=success,
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    # ===== Sesión =====

    async def save_session(self) -> ActionResult:
        """Guarda sesión actual (cookies, storage)."""
        start = datetime.utcnow()
        try:
            await self.session_manager.sync_from_browser(self.module_name, self.page.context)
            self.session_manager.save_profile(self.module_name, force=True)
            return ActionResult(
                success=True,
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    async def restore_session(self) -> ActionResult:
        """Restaura sesión guardada."""
        start = datetime.utcnow()
        try:
            await self.session_manager.sync_to_browser(self.module_name, self.page.context)
            return ActionResult(
                success=True,
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    # ===== Artefactos =====

    async def save_artifact(
        self,
        artifact_type: str,
        content: Union[bytes, str, Path],
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        filename: Optional[str] = None,
    ) -> ActionResult:
        start = datetime.utcnow()
        try:
            async with self.artifact_store.session(self.module_name) as session:
                artifact = await self.artifact_store.add_artifact(
                    session,
                    artifact_type,
                    content,
                    tags=tags,
                    metadata=metadata,
                    filename=filename,
                )
            return ActionResult(
                success=True,
                data={"artifact_id": artifact.artifact_id, "path": str(artifact.path)},
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    # ===== Info =====

    def get_url(self) -> str:
        return self.page.url

    def get_title(self) -> str:
        return self.page.title()

    def get_action_count(self) -> int:
        return self._action_count