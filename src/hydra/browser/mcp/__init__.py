"""
HYDRA Browser MCP - Interfaz MCP para automatización web.

Todos los agentes de HYDRA (Mail, Trading, Vault, Design, Skills, etc.)
deben comunicarse exclusivamente a través de este MCP.
Ningún agente usa Playwright directamente.
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from playwright.async_api import Download, FileChooser, Page

from hydra.browser.core.browser_pool import BrowserPool, BrowserContextConfig
from hydra.browser.core.session_manager import SessionManager
from hydra.browser.core.actions import BrowserActions
from hydra.browser.artifacts import ArtifactStore
from hydra.browser.vision import VisionAnalyzer
from hydra.browser.recorder import VideoRecorder, RecordingConfig
from hydra.browser.validation import ValidationEngine

logger = logging.getLogger(__name__)


@dataclass
class MCPRequest:
    """Request al MCP."""
    action: str
    params: Dict[str, Any]
    request_id: str
    agent_name: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class MCPResponse:
    """Response del MCP."""
    request_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    duration_ms: float = 0
    artifacts: List[str] = field(default_factory=list)


class HydraBrowserMCP:
    """
    MCP (Model Context Protocol) Server para HYDRA Browser.

    Expone acciones de alto nivel que los agentes pueden invocar.
    Gestiona lifecycle de navegador, sesiones, artefactos y validaciones.
    """

    def __init__(
        self,
        browser_pool: BrowserPool,
        session_manager: SessionManager,
        artifact_store: ArtifactStore,
        vision_analyzer: Optional[VisionAnalyzer] = None,
        video_recorder: Optional[VideoRecorder] = None,
        validation_engine: Optional[ValidationEngine] = None,
        default_module: str = "generic",
    ):
        self.browser_pool = browser_pool
        self.session_manager = session_manager
        self.artifact_store = artifact_store
        self.vision_analyzer = vision_analyzer
        self.video_recorder = video_recorder
        self.validation_engine = validation_engine
        self.default_module = default_module

        self._actions = BrowserActions(
            browser_pool=browser_pool,
            session_manager=session_manager,
            artifact_store=artifact_store,
            vision_analyzer=vision_analyzer,
        )

        self._registered_agents: Dict[str, Dict[str, Any]] = {}
        self._request_count = 0

    def register_agent(self, agent_name: str, config: Dict[str, Any]) -> None:
        """Registra un agente con su configuración (módulo, timeouts, etc.)."""
        self._registered_agents[agent_name] = config
        logger.info(f"Agente registrado: {agent_name} -> {config}")

    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """Obtiene configuración de un agente."""
        return self._registered_agents.get(agent_name, {})

    # ===== MCP Interface =====

    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """Procesa un request MCP y retorna response."""
        start = datetime.utcnow()
        request_id = request.request_id

        try:
            # Verificar agente autorizado
            if request.agent_name not in self._registered_agents:
                raise ValueError(f"Agente no registrado: {request.agent_name}")

            # Dispatch a acción
            handler = getattr(self, f"_mcp_{request.action}", None)
            if not handler:
                raise ValueError(f"Acción no soportada: {request.action}")

            result = await handler(request.params, request.agent_name)

            duration_ms = (datetime.utcnow() - start).total_seconds() * 1000

            return MCPResponse(
                request_id=request_id,
                success=True,
                result=result,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (datetime.utcnow() - start).total_seconds() * 1000
            logger.error(f"MCP error [{request_id}]: {e}")
            return MCPResponse(
                request_id=request_id,
                success=False,
                error=str(e),
                duration_ms=duration_ms,
            )

    # ===== High-level Actions (MCP endpoints) =====

    async def _mcp_open_page(
        self,
        params: Dict[str, Any],
        agent_name: str,
    ) -> Dict[str, Any]:
        """Abre una página web."""
        url = params["url"]
        wait_until = params.get("wait_until", "networkidle")
        context_config = self._get_context_config(params, agent_name)

        async with self.browser_pool.acquire(context_config) as context:
            page = await self.browser_pool.create_page(context)
            try:
                await page.goto(url, wait_until=wait_until)
                return {"url": page.url, "title": await page.title()}
            finally:
                await self.browser_pool.close_page(context, page)

    async def _mcp_click(
        self,
        params: Dict[str, Any],
        agent_name: str,
    ) -> Dict[str, Any]:
        """Click en elemento."""
        selector = params["selector"]
        context_config = self._get_context_config(params, agent_name)

        async with self.browser_pool.acquire(context_config) as context:
            page = await self.browser_pool.create_page(context)
            try:
                await page.locator(selector).click()
                return {"success": True}
            finally:
                await self.browser_pool.close_page(context, page)

    async def _mcp_double_click(
        self,
        params: Dict[str, Any],
        agent_name: str,
    ) -> Dict[str, Any]:
        selector = params["selector"]
        context_config = self._get_context_config(params, agent_name)

        async with self.browser_pool.acquire(context_config) as context:
            page = await self.browser_pool.create_page(context)
            try:
                await page.locator(selector).dblclick()
                return {"success": True}
            finally:
                await self.browser_pool.close_page(context, page)

    async def _mcp_hover(
        self,
        params: Dict[str, Any],
        agent_name: str,
    ) -> Dict[str, Any]:
        selector = params["selector"]
        context_config = self._get_context_config(params, agent_name)

        async with self.browser_pool.acquire(context_config) as context:
            page = await self.browser_pool.create_page(context)
            try:
                await page.locator(selector).hover()
                return {"success": True}
            finally:
                await self.browser_pool.close_page(context, page)

    async def _mcp_fill(
        self,
        params: Dict[str, Any],
        agent_name: str,
    ) -> Dict[str, Any]:
        """Rellena un campo."""
        selector = params["selector"]
        value = params["value"]
        clear_first = params.get("clear_first", True)
        context_config = self._get_context_config(params, agent_name)

        async with self.browser_pool.acquire(context_config) as context:
            page = await self.browser_pool.create_page(context)
            try:
                locator = page.locator(selector)
                if clear_first:
                    await locator.clear()
                await locator.fill(value)
                return {"success": True}
            finally:
                await self.browser_pool.close_page(context, page)

    async def _mcp_press_key(
        self,
        params: Dict[str, Any],
        agent_name: str,
    ) -> Dict[str, Any]:
        selector = params["selector"]
        key = params["key"]
        modifiers = params.get("modifiers")
        context_config = self._get_context_config(params, agent_name)

        async with self.browser_pool.acquire(context_config) as context:
            page = await self.browser_pool.create_page(context)
            try:
                await page.locator(selector).press(key, modifiers=modifiers)
                return {"success": True}
            finally:
                await self.browser_pool.close_page(context, page)

    async def _mcp_upload_file(
        self,
        params: Dict[str, Any],
        agent_name: str,
    ) -> Dict[str, Any]:
        selector = params["selector"]
        file_path = params["file_path"]
        context_config = self._get_context_config(params, agent_name)

        async with self.browser_pool.acquire(context_config) as context:
            page = await self.browser_pool.create_page(context)
            try:
                await page.locator(selector).set_input_files(file_path)
                return {"success": True}
            finally:
                await self.browser_pool.close_page(context, page)

    async def _mcp_download_file(
        self,
        params: Dict[str, Any],
        agent_name: str,
    ) -> Dict[str, Any]:
        selector = params["selector"]
        save_path = params.get("save_path")
        context_config = self._get_context_config(params, agent_name)

        async with self.browser_pool.acquire(context_config) as context:
            page = await self.browser_pool.create_page(context)
            try:
                async with page.expect_download() as download_info:
                    await page.locator(selector).click()
                download: Download = await download_info.value
                if save_path:
                    await download.save_as(save_path)
                return {"path": save_path or download.path(), "suggested_filename": download.suggested_filename}
            finally:
                await self.browser_pool.close_page(context, page)

    async def _mcp_take_screenshot(
        self,
        params: Dict[str, Any],
        agent_name: str,
    ) -> Dict[str, Any]:
        """Captura screenshot."""
        full_page = params.get("full_page", True)
        selector = params.get("selector")
        save_path = params.get("save_path")
        context_config = self._get_context_config(params, agent_name)

        async with self.browser_pool.acquire(context_config) as context:
            page = await self.browser_pool.create_page(context)
            try:
                if selector:
                    content = await page.locator(selector).screenshot(path=save_path, type="png")
                else:
                    content = await page.screenshot(path=save_path, full_page=full_page, type="png")
                return {"path": save_path, "size": len(content) if isinstance(content, bytes) else 0}
            finally:
                await self.browser_pool.close_page(context, page)

    async def _mcp_record_video(
        self,
        params: Dict[str, Any],
        agent_name: str,
    ) -> Dict[str, Any]:
        """Inicia/para grabación de video."""
        action = params["action"]  # "start" | "stop"
        session_id = params.get("session_id")

        if action == "start":
            if not self.video_recorder:
                raise RuntimeError("VideoRecorder no configurado")
            context_config = self._get_context_config(params, agent_name)
            async with self.browser_pool.acquire(context_config) as context:
                # La grabación se maneja via context manager
                return {"session_id": session_id, "started": True}
        elif action == "stop":
            # Se maneja al salir del context manager
            return {"session_id": session_id, "stopped": True}
        else:
            raise ValueError(f"Acción de video inválida: {action}")

    async def _mcp_extract_text(
        self,
        params: Dict[str, Any],
        agent_name: str,
    ) -> Dict[str, Any]:
        """Extrae texto de elemento o página."""
        selector = params.get("selector")
        context_config = self._get_context_config(params, agent_name)

        async with self.browser_pool.acquire(context_config) as context:
            page = await self.browser_pool.create_page(context)
            try:
                if selector:
                    text = await page.locator(selector).text_content()
                else:
                    text = await page.text_content("body")
                return {"text": text.strip() if text else ""}
            finally:
                await self.browser_pool.close_page(context, page)

    async def _mcp_extract_table(
        self,
        params: Dict[str, Any],
        agent_name: str,
    ) -> Dict[str, Any]:
        """Extrae tabla HTML."""
        selector = params["selector"]
        context_config = self._get_context_config(params, agent_name)

        async with self.browser_pool.acquire(context_config) as context:
            page = await self.browser_pool.create_page(context)
            try:
                rows = await page.locator(f"{selector} tr").all()
                data = []
                for row in rows:
                    cells = await row.locator("td, th").all()
                    row_data = []
                    for cell in cells:
                        row_data.append((await cell.text_content() or "").strip())
                    data.append(row_data)
                return {"table": data}
            finally:
                await self.browser_pool.close_page(context, page)

    async def _mcp_wait_selector(
        self,
        params: Dict[str, Any],
        agent_name: str,
    ) -> Dict[str, Any]:
        """Espera selector."""
        selector = params["selector"]
        state = params.get("state", "visible")
        timeout = params.get("timeout", 10000)
        context_config = self._get_context_config(params, agent_name)

        async with self.browser_pool.acquire(context_config) as context:
            page = await self.browser_pool.create_page(context)
            try:
                await page.locator(selector).wait_for(state=state, timeout=timeout)
                return {"success": True}
            finally:
                await self.browser_pool.close_page(context, page)

    async def _mcp_wait_text(
        self,
        params: Dict[str, Any],
        agent_name: str,
    ) -> Dict[str, Any]:
        """Espera texto en página."""
        text = params["text"]
        selector = params.get("selector", "body")
        timeout = params.get("timeout", 10000)
        context_config = self._get_context_config(params, agent_name)

        async with self.browser_pool.acquire(context_config) as context:
            page = await self.browser_pool.create_page(context)
            try:
                locator = page.locator(selector)
                await locator.wait_for(state="visible", timeout=timeout)

                # Polling
                import time
                start = time.time()
                max_wait = timeout / 1000
                while time.time() - start < max_wait:
                    content = await locator.text_content()
                    if content and text in content:
                        return {"success": True, "found": True}
                    await asyncio.sleep(0.1)
                return {"success": True, "found": False}
            finally:
                await self.browser_pool.close_page(context, page)

    async def _mcp_wait_download(
        self,
        params: Dict[str, Any],
        agent_name: str,
    ) -> Dict[str, Any]:
        selector = params["trigger_selector"]
        save_path = params.get("save_path")
        timeout = params.get("timeout", 30000)
        context_config = self._get_context_config(params, agent_name)

        async with self.browser_pool.acquire(context_config) as context:
            page = await self.browser_pool.create_page(context)
            try:
                async with page.expect_download(timeout=timeout) as download_info:
                    await page.locator(selector).click()
                download = await download_info.value
                if save_path:
                    await download.save_as(save_path)
                return {"path": save_path or download.path(), "filename": download.suggested_filename}
            finally:
                await self.browser_pool.close_page(context, page)

    async def _mcp_compile_pine(
        self,
        params: Dict[str, Any],
        agent_name: str,
    ) -> Dict[str, Any]:
        """Compila script Pine en TradingView."""
        if not self.validation_engine:
            raise RuntimeError("ValidationEngine no configurado")

        script = params["script"]
        script_name = params.get("script_name", "script.pine")

        # Usar validation engine
        async with self.validation_engine.validate(script, script_name, "tradingview") as report:
            return {
                "status": report.status.value,
                "compilation": report.compilation.to_dict() if hasattr(report.compilation, 'to_dict') else report.compilation,
                "screenshots": report.screenshots,
                "metrics": report.metrics,
            }

    async def _mcp_publish_post(
        self,
        params: Dict[str, Any],
        agent_name: str,
    ) -> Dict[str, Any]:
        """Publica post (genérico, delega a módulo)."""
        module_name = params.get("module", self.default_module)
        module = self.validation_engine.get_module(module_name) if self.validation_engine else None
        if not module or not hasattr(module, "publish_post"):
            raise ValueError(f"Módulo {module_name} no soporta publish_post")
        return await module.publish_post(params)

    async def _mcp_upload_video(
        self,
        params: Dict[str, Any],
        agent_name: str,
    ) -> Dict[str, Any]:
        """Sube video (delega a módulo específico)."""
        module_name = params.get("module", self.default_module)
        module = self.validation_engine.get_module(module_name) if self.validation_engine else None
        if not module or not hasattr(module, "upload_video"):
            raise ValueError(f"Módulo {module_name} no soporta upload_video")
        return await module.upload_video(params)

    async def _mcp_login(
        self,
        params: Dict[str, Any],
        agent_name: str,
    ) -> Dict[str, Any]:
        """Login en servicio."""
        module_name = params.get("module", self.default_module)
        module = self.validation_engine.get_module(module_name) if self.validation_engine else None
        if not module or not hasattr(module, "login"):
            raise ValueError(f"Módulo {module_name} no soporta login")

        context_config = self._get_context_config(params, agent_name)
        async with self.browser_pool.acquire(context_config) as context:
            page = await self.browser_pool.create_page(context)
            try:
                result = await module.login(page, params.get("credentials", {}))
                await self.session_manager.sync_from_browser(module.service_name, context)
                return result
            finally:
                await self.browser_pool.close_page(context, page)

    async def _mcp_logout(
        self,
        params: Dict[str, Any],
        agent_name: str,
    ) -> Dict[str, Any]:
        """Logout de servicio."""
        module_name = params.get("module", self.default_module)
        module = self.validation_engine.get_module(module_name) if self.validation_engine else None
        if not module or not hasattr(module, "logout"):
            raise ValueError(f"Módulo {module_name} no soporta logout")
        return await module.logout(params)

    async def _mcp_save_session(
        self,
        params: Dict[str, Any],
        agent_name: str,
    ) -> Dict[str, Any]:
        """Guarda sesión actual."""
        module_name = params.get("module", self.default_module)
        context_config = self._get_context_config(params, agent_name)

        async with self.browser_pool.acquire(context_config) as context:
            await self.session_manager.sync_from_browser(module_name, context)
            self.session_manager.save_profile(module_name, force=True)
            return {"success": True}

    async def _mcp_restore_session(
        self,
        params: Dict[str, Any],
        agent_name: str,
    ) -> Dict[str, Any]:
        """Restaura sesión guardada."""
        module_name = params.get("module", self.default_module)
        context_config = self._get_context_config(params, agent_name)

        async with self.browser_pool.acquire(context_config) as context:
            await self.session_manager.sync_to_browser(module_name, context)
            return {"success": True}

    # ===== Helpers =====

    def _get_context_config(
        self,
        params: Dict[str, Any],
        agent_name: str,
    ) -> Optional[BrowserContextConfig]:
        """Obtiene configuración de contexto desde params o agente."""
        if "context" in params:
            return BrowserContextConfig(**params["context"])

        agent_config = self.get_agent_config(agent_name)
        if "context" in agent_config:
            return BrowserContextConfig(**agent_config["context"])

        return BrowserContextConfig(profile_name=agent_config.get("module", self.default_module))

    # ===== Convenience methods para agentes =====

    @asynccontextmanager
    async def session(self, agent_name: str, module: Optional[str] = None):
        """Context manager para sesión completa de un agente."""
        module = module or self.get_agent_config(agent_name).get("module", self.default_module)
        context_config = BrowserContextConfig(profile_name=module)

        async with self.browser_pool.acquire(context_config) as context:
            # Restaurar sesión si existe
            await self.session_manager.sync_to_browser(module, context)

            page = await self.browser_pool.create_page(context)

            try:
                yield BrowserActions(
                    page=page,
                    browser_pool=self.browser_pool,
                    session_manager=self.session_manager,
                    artifact_store=self.artifact_store,
                    vision_analyzer=self.vision_analyzer,
                    module_name=module,
                )
            finally:
                # Guardar sesión al salir
                await self.session_manager.sync_from_browser(module, context)
                self.session_manager.save_profile(module, force=True)
                await self.browser_pool.close_page(context, page)

    async def run_validation(
        self,
        agent_name: str,
        script: str,
        script_name: str,
        module: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Ejecuta validación completa (para agentes de trading)."""
        if not self.validation_engine:
            raise RuntimeError("ValidationEngine no configurado")

        module = module or self.get_agent_config(agent_name).get("module", self.default_module)
        async with self.validation_engine.validate(script, script_name, module) as report:
            return report.to_dict()