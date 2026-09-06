"""
TradingView Connector — Implementación del conector TradingView.

Usa BaseConnector y se registra automáticamente.
Toda la lógica de TradingView vive aquí, BrowserManager solo provee infraestructura.
"""

import asyncio
import json
import logging
import pyotp
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from hydra.browser.connectors import (
    BaseConnector,
    ConnectorConfig,
    ConnectorCapabilities,
    Capability,
    register_connector,
    AuthMixin,
)
from hydra.browser.connectors.capabilities import get_capabilities
from hydra.browser.core.page_objects import BasePageObject, Selector
from hydra.browser.artifacts import ArtifactStore
from hydra.browser.validation import CompilationError, CompilationResult, ErrorType, PineErrorParser
from hydra.browser.vision import VisionAnalyzer

logger = logging.getLogger(__name__)


# ===== Page Objects =====

class TradingViewLoginPage(BasePageObject):
    def _initialize_selectors(self) -> None:
        self.register_selector("email_input", Selector(
            data_name="email-input",
            css="input[type='email']",
            xpath="//input[@type='email']",
        ))
        self.register_selector("password_input", Selector(
            data_name="password-input",
            css="input[type='password']",
            xpath="//input[@type='password']",
        ))
        self.register_selector("sign_in_button", Selector(
            data_name="sign-in-button",
            text="Sign in",
            role="button",
        ))
        self.register_selector("2fa_input", Selector(
            data_name="2fa-input",
            css="input[name='totp']",
        ))
        self.register_selector("2fa_submit", Selector(
            data_name="2fa-submit",
            text="Verify",
            role="button",
        ))

    async def login(self, email: str, password: str, totp_secret: Optional[str] = None) -> bool:
        try:
            await self.fill("email_input", email)
            await self.fill("password_input", password)
            await self.click("sign_in_button")

            if await self.is_visible("2fa_input", timeout=5000):
                if not totp_secret:
                    raise ValueError("Se requiere TOTP secret para 2FA")
                code = pyotp.TOTP(totp_secret).now()
                await self.fill("2fa_input", code)
                await self.click("2fa_submit")

            await self.wait_for_url("**/chart/**", timeout=30000)
            return True
        except Exception as e:
            logger.error(f"Login falló: {e}")
            return False


class TradingViewChartPage(BasePageObject):
    def _initialize_selectors(self) -> None:
        self.register_selector("pine_editor_tab", Selector(
            data_name="pane-tab-pine",
            text="Pine Editor",
            role="tab",
        ))
        self.register_selector("add_to_chart_button", Selector(
            data_name="add-to-chart",
            text="Add to chart",
        ))
        self.register_selector("pine_editor_textarea", Selector(
            data_name="pine-editor",
            css=".pine-editor .monaco-editor textarea",
            xpath="//div[contains(@class, 'pine-editor')]//textarea",
        ))
        self.register_selector("error_panel", Selector(
            data_name="pine-errors",
            css=".pine-editor-errors, .errors-panel",
        ))
        self.register_selector("error_list", Selector(
            css=".pine-editor-errors .error-item, .errors-panel .error",
        ))
        self.register_selector("compile_status", Selector(
            data_name="compile-status",
            css=".compile-status, .pine-status",
        ))
        self.register_selector("chart_canvas", Selector(
            css=".chart-container canvas, .tv-chart-container canvas",
        ))

    async def open_pine_editor(self) -> bool:
        try:
            await self.click("pine_editor_tab")
            await self.wait_for_selector("pine_editor_textarea", state="visible")
            return True
        except Exception as e:
            logger.error(f"Error abriendo Pine Editor: {e}")
            return False

    async def load_script(self, script_content: str) -> bool:
        try:
            await self.page.evaluate(f"""
                (() => {{
                    const editor = document.querySelector('.pine-editor .monaco-editor');
                    if (editor && editor.monacoEditor) {{
                        editor.monacoEditor.setValue({json.dumps(script_content)});
                        return true;
                    }}
                    const textarea = document.querySelector('.pine-editor textarea');
                    if (textarea) {{
                        textarea.value = {json.dumps(script_content)};
                        textarea.dispatchEvent(new Event('input', {{bubbles: true}}));
                        return true;
                    }}
                    return false;
                }})()
            """)
            await asyncio.sleep(0.5)
            return True
        except Exception as e:
            logger.error(f"Error cargando script: {e}")
            return False

    async def click_add_to_chart(self) -> bool:
        try:
            await self.click("add_to_chart_button")
            return True
        except Exception as e:
            logger.error(f"Error en Add to chart: {e}")
            return False

    async def wait_for_compilation(self, timeout: float = 60000) -> bool:
        try:
            await self.page.wait_for_function(
                """() => {
                    const status = document.querySelector('[data-name="compile-status"], .compile-status, .pine-status');
                    if (!status) return false;
                    const text = status.textContent.toLowerCase();
                    return text.includes('success') || text.includes('error') || text.includes('compil');
                }""",
                timeout=timeout,
            )
            return True
        except PlaywrightTimeoutError:
            return False

    async def get_compilation_errors(self) -> List[Dict[str, Any]]:
        try:
            if not await self.is_visible("error_panel", timeout=3000):
                return []

            error_items = await self.page.locator(".pine-editor-errors .error-item, .errors-panel .error").all()
            errors = []
            for item in error_items:
                text = await item.text_content()
                if text:
                    errors.append({"raw": text.strip(), "element": item})
            return errors
        except Exception as e:
            logger.error(f"Error extrayendo errores: {e}")
            return []

    async def screenshot_chart(self, path: Path) -> bool:
        try:
            locator = self.selector("chart_canvas").to_playwright_locator(self.page)
            await locator.screenshot(path=path, type="png")
            return True
        except Exception:
            await self.page.screenshot(path=path, full_page=True, type="png")
            return True


# ===== Config =====

@dataclass
class TradingViewConnectorConfig:
    email: str
    password: str
    totp_secret: Optional[str] = None
    base_url: str = "https://www.tradingview.com"
    default_symbol: str = "NASDAQ:AAPL"


# ===== Connector Implementation =====

class TradingViewConnector(BaseConnector, AuthMixin):
    """
    Conector TradingView implementando BaseConnector.
    
    Capacidades:
    - login: Autenticación email/password + 2FA TOTP
    - health_check: Verifica acceso a TradingView
    - compile_pine: Compila script Pine en TradingView real
    - chart_navigation: Navegación a gráficos
    - pine_editor: Control Pine Editor
    - screenshot: Capturas de gráfico y panel de errores
    """
    
    # Registrar conector automáticamente
    _capabilities = get_capabilities("tradingview")
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.tv_config = TradingViewConnectorConfig(
            email=config.credentials.get("email", ""),
            password=config.credentials.get("password", ""),
            totp_secret=config.credentials.get("totp_secret"),
            base_url=config.custom_config.get("base_url", "https://www.tradingview.com"),
            default_symbol=config.custom_config.get("default_symbol", "NASDAQ:AAPL"),
        )
        self._artifact_store: Optional[ArtifactStore] = None
        self._vision_analyzer: Optional[VisionAnalyzer] = None
        self._logged_in = False
    
    @property
    def capabilities(self) -> ConnectorCapabilities:
        return self._capabilities
    
    # ===== BaseConnector Implementation =====
    
    async def _perform_health_check(self) -> bool:
        """Verifica disponibilidad de TradingView."""
        if not self._browser_manager:
            return False
        
        try:
            async with self._browser_manager.session("tradingview") as actions:
                await actions.goto(f"{self.tv_config.base_url}/chart/")
                await actions.wait_for_load_state("networkidle", timeout=10000)
                return "signin" not in actions.get_url()
        except Exception:
            return False
    
    async def login(self, credentials: Optional[Dict[str, Any]] = None) -> bool:
        """Login en TradingView."""
        creds = credentials or {
            "email": self.tv_config.email,
            "password": self.tv_config.password,
            "totp_secret": self.tv_config.totp_secret,
        }
        
        async with self._browser_manager.session("tradingview") as actions:
            # Verificar si ya está logueado
            await actions.goto(f"{self.tv_config.base_url}/chart/")
            await actions.wait_for_load_state("networkidle", timeout=10000)
            
            if "signin" not in actions.get_url():
                logger.info("Sesión TradingView ya válida")
                self._logged_in = True
                return True
            
            # Login fresco
            login_page = TradingViewLoginPage(actions.page, base_url=self.tv_config.base_url)
            await login_page.goto("/accounts/signin/")
            
            success = await login_page.login(
                creds.get("email", self.tv_config.email),
                creds.get("password", self.tv_config.password),
                creds.get("totp_secret", self.tv_config.totp_secret),
            )
            
            if success:
                self._logged_in = True
                logger.info("Login TradingView exitoso")
            else:
                logger.error("Login TradingView falló")
            
            return success
    
    async def _execute_compile_pine(self, params: Dict[str, Any]) -> Any:
        """Ejecuta compilación de script Pine."""
        script_content = params["script"]
        script_name = params.get("script_name", "script.pine")
        symbol = params.get("symbol", self.tv_config.default_symbol)
        timeout = params.get("timeout", 60000)
        
        if not await self._ensure_logged_in():
            return CompilationResult(
                success=False,
                errors=[CompilationError(
                    line=0, column=0,
                    message="No se pudo iniciar sesión en TradingView",
                    code="AUTH_FAILED",
                    severity="error",
                    error_type=ErrorType.UNKNOWN,
                )],
            )
        
        start = datetime.utcnow()
        
        async with self._browser_manager.session("tradingview") as actions:
            chart_page = TradingViewChartPage(actions.page, base_url=self.tv_config.base_url)
            
            # 1. Ir a gráfico
            await chart_page.goto(f"/chart/?symbol={symbol}")
            
            # 2. Abrir Pine Editor
            if not await chart_page.open_pine_editor():
                return CompilationResult(
                    success=False,
                    errors=[CompilationError(
                        line=0, column=0,
                        message="No se pudo abrir Pine Editor",
                        code="EDITOR_ERROR",
                        severity="error",
                        error_type=ErrorType.UNKNOWN,
                    )],
                )
            
            # 3. Cargar script
            if not await chart_page.load_script(script_content):
                return CompilationResult(
                    success=False,
                    errors=[CompilationError(
                        line=0, column=0,
                        message="No se pudo cargar script en editor",
                        code="LOAD_ERROR",
                        severity="error",
                        error_type=ErrorType.UNKNOWN,
                    )],
                )
            
            # 4. Click Add to chart
            await chart_page.click_add_to_chart()
            
            # 5. Esperar compilación
            await chart_page.wait_for_compilation(timeout=timeout)
            
            # 6. Capturar errores
            raw_errors = await chart_page.get_compilation_errors()
            error_text = "\n".join(e["raw"] for e in raw_errors)
            
            # 7. Parsear errores
            parsed_errors = PineErrorParser.parse_errors(error_text)
            parsed_warnings = PineErrorParser.parse_warnings(error_text)
            
            # 8. Screenshots y artifacts
            screenshots = {}
            if self._artifact_store:
                async with self._artifact_store.session("tradingview") as session:
                    # Script
                    await self._artifact_store.add_script(session, script_content, script_name)
                    
                    # Chart screenshot
                    chart_path = Path(f"chart_{datetime.utcnow().strftime('%H%M%S')}.png")
                    await chart_page.screenshot_chart(chart_path)
                    await self._artifact_store.add_artifact(
                        session, "screenshot", chart_path,
                        tags=["chart", "compilation"],
                        metadata={"phase": "post_compilation"},
                    )
                    screenshots["chart"] = str(chart_path)
                    
                    # Error screenshot si hay errores
                    if parsed_errors:
                        error_path = Path(f"errors_{datetime.utcnow().strftime('%H%M%S')}.png")
                        await actions.screenshot(str(error_path), full_page=True)
                        await self._artifact_store.add_artifact(
                            session, "screenshot", error_path,
                            tags=["errors", "compilation"],
                        )
                        screenshots["errors"] = str(error_path)
            
            # 9. Vision analysis
            if self._vision_analyzer:
                try:
                    analysis = await self._vision_analyzer.analyze(actions.page)
                    if analysis.detected_states.get("error") and not parsed_errors:
                        parsed_errors.append(CompilationError(
                            line=0, column=0,
                            message="Error visual detectado en UI",
                            code="VISUAL_ERROR",
                            severity="error",
                            error_type=ErrorType.RUNTIME,
                        ))
                except Exception as e:
                    logger.warning(f"Vision analysis falló: {e}")
            
            duration_ms = (datetime.utcnow() - start).total_seconds() * 1000
            
            return CompilationResult(
                success=len(parsed_errors) == 0,
                errors=parsed_errors,
                warnings=parsed_warnings,
                duration_ms=duration_ms,
            )
    
    # ===== Capability Methods =====
    
    async def _execute_login(self, params: Dict[str, Any]) -> Any:
        return await self.login(params.get("credentials"))
    
    async def _execute_health_check(self, params: Dict[str, Any]) -> Any:
        healthy = await self._perform_health_check()
        return {"healthy": healthy}
    
    async def _execute_chart_navigation(self, params: Dict[str, Any]) -> Any:
        if not await self._ensure_logged_in():
            return {"success": False, "error": "No autenticado"}
        
        async with self._browser_manager.session("tradingview") as actions:
            symbol = params.get("symbol", self.tv_config.default_symbol)
            await actions.goto(f"{self.tv_config.base_url}/chart/?symbol={symbol}")
            return {"success": True, "url": actions.get_url()}
    
    async def _execute_pine_editor(self, params: Dict[str, Any]) -> Any:
        if not await self._ensure_logged_in():
            return {"success": False, "error": "No autenticado"}
        
        async with self._browser_manager.session("tradingview") as actions:
            chart_page = TradingViewChartPage(actions.page, base_url=self.tv_config.base_url)
            await chart_page.goto(f"/chart/?symbol={self.tv_config.default_symbol}")
            
            action = params.get("action")
            if action == "open":
                success = await chart_page.open_pine_editor()
                return {"success": success}
            elif action == "load_script":
                script = params.get("script", "")
                success = await chart_page.load_script(script)
                return {"success": success}
            elif action == "add_to_chart":
                success = await chart_page.click_add_to_chart()
                return {"success": success}
            elif action == "get_errors":
                errors = await chart_page.get_compilation_errors()
                return {"success": True, "errors": errors}
            elif action == "get_content":
                content = await chart_page.get_script_content()
                return {"success": True, "content": content}
            
            return {"success": False, "error": f"Acción pine_editor no soportada: {action}"}
    
    async def _execute_screenshot(self, params: Dict[str, Any]) -> Any:
        if not await self._ensure_logged_in():
            return {"success": False, "error": "No autenticado"}
        
        async with self._browser_manager.session("tradingview") as actions:
            chart_page = TradingViewChartPage(actions.page, base_url=self.tv_config.base_url)
            path = params.get("path", f"screenshot_{datetime.utcnow().strftime('%H%M%S')}.png")
            path = Path(path)
            
            screenshot_type = params.get("type", "chart")
            if screenshot_type == "chart":
                success = await chart_page.screenshot_chart(path)
            else:
                success = await actions.screenshot(str(path), full_page=True)
            
            return {"success": success, "path": str(path) if success else None}
    
    async def _execute_chart_navigation(self, params: Dict[str, Any]) -> Any:
        return await self._execute_chart_navigation(params)
    
    # ===== Helpers =====
    
    async def _ensure_logged_in(self) -> bool:
        if not self._logged_in:
            return await self.login()
        return True
    
    async def _cleanup(self) -> None:
        self._logged_in = False
    
    # ===== Inyección de dependencias =====
    
    def set_artifact_store(self, store: ArtifactStore) -> None:
        self._artifact_store = store
    
    def set_vision_analyzer(self, analyzer: VisionAnalyzer) -> None:
        self._vision_analyzer = analyzer


# ===== Registro Automático =====

# El conector se registra automáticamente al importarse
register_connector(
    name="tradingview",
    connector_class=TradingViewConnector,
    capabilities=get_capabilities("tradingview"),
    version="1.0.0",
    description="Automatización TradingView: login, Pine Editor, compilación, screenshots",
    dependencies=[],
)

# Para compatibilidad con auto-discovery
CONNECTOR_CLASS = TradingViewConnector
CONNECTOR_CAPABILITIES = get_capabilities("tradingview")