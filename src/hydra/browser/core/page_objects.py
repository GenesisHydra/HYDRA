"""
Page Objects Base - Patrón Page Object Model para HYDRA Browser.

Proporciona una base común para todos los módulos de sitios web,
con selectores robustos, esperas inteligentes y logging estructurado.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from playwright.async_api import ElementHandle, Locator, Page, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)


@dataclass
class Selector:
    """Selector robusto con múltiples estrategias de fallback."""
    # Selectores en orden de prioridad
    data_testid: Optional[str] = None
    data_name: Optional[str] = None
    aria_label: Optional[str] = None
    role: Optional[str] = None
    text: Optional[str] = None
    css: Optional[str] = None
    xpath: Optional[str] = None
    # Configuración
    timeout: float = 10000
    state: str = "visible"  # attached, visible, hidden, detached
    strict: bool = True

    def to_playwright_locator(self, page: Page) -> Locator:
        """Convierte a locator de Playwright usando la mejor estrategia disponible."""
        if self.data_testid:
            return page.get_by_test_id(self.data_testid)
        if self.data_name:
            return page.get_by_attribute("data-name", self.data_name)
        if self.aria_label:
            return page.get_by_label(self.aria_label, exact=True)
        if self.role:
            return page.get_by_role(self.role, name=self.text)
        if self.text:
            return page.get_by_text(self.text, exact=True)
        if self.css:
            return page.locator(self.css)
        if self.xpath:
            return page.locator(f"xpath={self.xpath}")
        raise ValueError("Selector sin estrategia válida")

    def __str__(self) -> str:
        parts = []
        if self.data_testid: parts.append(f"testid={self.data_testid}")
        if self.data_name: parts.append(f"data-name={self.data_name}")
        if self.aria_label: parts.append(f"aria-label={self.aria_label}")
        if self.role: parts.append(f"role={self.role}")
        if self.text: parts.append(f"text={self.text[:30]}")
        if self.css: parts.append(f"css={self.css}")
        if self.xpath: parts.append(f"xpath={self.xpath}")
        return f"Selector([{', '.join(parts)}])"


@dataclass
class WaitConfig:
    """Configuración de espera para acciones."""
    timeout: float = 10000
    state: str = "visible"
    poll_interval: float = 100
    retries: int = 2
    retry_delay: float = 500


class BasePageObject(ABC):
    """
    Clase base para Page Objects.

    Cada módulo (TradingView, Gmail, etc.) debe crear sus Page Objects
    heredando de esta clase y definiendo sus selectores y acciones.
    """

    def __init__(
        self,
        page: Page,
        base_url: str = "",
        default_timeout: float = 10000,
    ):
        self.page = page
        self.base_url = base_url.rstrip("/")
        self.default_timeout = default_timeout
        self._selectors: Dict[str, Selector] = {}
        self._initialize_selectors()

    @abstractmethod
    def _initialize_selectors(self) -> None:
        """Define los selectores específicos de esta página."""
        pass

    def selector(self, name: str) -> Selector:
        """Obtiene un selector por nombre."""
        if name not in self._selectors:
            raise KeyError(f"Selector '{name}' no definido en {self.__class__.__name__}")
        return self._selectors[name]

    def register_selector(self, name: str, selector: Selector) -> None:
        """Registra un selector."""
        self._selectors[name] = selector

    # ===== Acciones básicas =====

    async def goto(self, path: str = "", wait_until: str = "networkidle") -> None:
        """Navega a una URL relativa al base_url."""
        url = f"{self.base_url}/{path.lstrip('/')}" if path else self.base_url
        logger.debug(f"Navegando a: {url}")
        await self.page.goto(url, wait_until=wait_until, timeout=self.default_timeout)

    async def click(
        self,
        selector_name: str,
        wait_config: Optional[WaitConfig] = None,
        force: bool = False,
    ) -> None:
        """Click en elemento con espera y reintentos."""
        selector = self.selector(selector_name)
        wc = wait_config or WaitConfig(timeout=self.default_timeout)
        locator = selector.to_playwright_locator(self.page)

        for attempt in range(wc.retries + 1):
            try:
                await locator.wait_for(state=wc.state, timeout=wc.timeout)
                await locator.click(force=force, timeout=wc.timeout)
                logger.debug(f"Click: {selector_name}")
                return
            except PlaywrightTimeoutError:
                if attempt == wc.retries:
                    raise
                await asyncio.sleep(wc.retry_delay / 1000)

    async def double_click(self, selector_name: str) -> None:
        """Doble click."""
        locator = self.selector(selector_name).to_playwright_locator(self.page)
        await locator.dblclick(timeout=self.default_timeout)

    async def hover(self, selector_name: str) -> None:
        """Hover sobre elemento."""
        locator = self.selector(selector_name).to_playwright_locator(self.page)
        await locator.hover(timeout=self.default_timeout)

    async def fill(
        self,
        selector_name: str,
        value: str,
        wait_config: Optional[WaitConfig] = None,
        clear_first: bool = True,
    ) -> None:
        """Rellena un campo de entrada."""
        selector = self.selector(selector_name)
        wc = wait_config or WaitConfig(timeout=self.default_timeout)
        locator = selector.to_playwright_locator(self.page)

        await locator.wait_for(state=wc.state, timeout=wc.timeout)
        if clear_first:
            await locator.clear(timeout=wc.timeout)
        await locator.fill(value, timeout=wc.timeout)
        logger.debug(f"Fill: {selector_name} = {value[:50]}")

    async def press_key(
        self,
        selector_name: str,
        key: str,
        modifiers: Optional[List[str]] = None,
    ) -> None:
        """Presiona una tecla (Enter, Tab, ArrowDown, etc.)."""
        locator = self.selector(selector_name).to_playwright_locator(self.page)
        await locator.press(key, modifiers=modifiers, timeout=self.default_timeout)

    async def select_option(
        self,
        selector_name: str,
        value: Union[str, List[str]],
    ) -> None:
        """Selecciona opción en dropdown."""
        locator = self.selector(selector_name).to_playwright_locator(self.page)
        await locator.select_option(value, timeout=self.default_timeout)

    async def check(self, selector_name: str) -> None:
        """Marca checkbox/radio."""
        locator = self.selector(selector_name).to_playwright_locator(self.page)
        await locator.check(timeout=self.default_timeout)

    async def uncheck(self, selector_name: str) -> None:
        """Desmarca checkbox."""
        locator = self.selector(selector_name).to_playwright_locator(self.page)
        await locator.uncheck(timeout=self.default_timeout)

    # ===== Extracción de datos =====

    async def get_text(
        self,
        selector_name: str,
        wait_config: Optional[WaitConfig] = None,
    ) -> str:
        """Obtiene el texto visible de un elemento."""
        selector = self.selector(selector_name)
        wc = wait_config or WaitConfig(timeout=self.default_timeout)
        locator = selector.to_playwright_locator(self.page)
        await locator.wait_for(state=wc.state, timeout=wc.timeout)
        return (await locator.text_content(timeout=wc.timeout) or "").strip()

    async def get_attribute(
        self,
        selector_name: str,
        attribute: str,
    ) -> Optional[str]:
        """Obtiene un atributo del elemento."""
        locator = self.selector(selector_name).to_playwright_locator(self.page)
        return await locator.get_attribute(attribute, timeout=self.default_timeout)

    async def get_value(self, selector_name: str) -> str:
        """Obtiene el value de un input."""
        locator = self.selector(selector_name).to_playwright_locator(self.page)
        return await locator.input_value(timeout=self.default_timeout)

    async def is_visible(self, selector_name: str, timeout: float = 5000) -> bool:
        """Verifica si elemento es visible."""
        try:
            locator = self.selector(selector_name).to_playwright_locator(self.page)
            await locator.wait_for(state="visible", timeout=timeout)
            return True
        except PlaywrightTimeoutError:
            return False

    async def is_enabled(self, selector_name: str) -> bool:
        """Verifica si elemento está habilitado."""
        locator = self.selector(selector_name).to_playwright_locator(self.page)
        return await locator.is_enabled(timeout=self.default_timeout)

    async def count(self, selector_name: str) -> int:
        """Cuenta elementos que coinciden."""
        locator = self.selector(selector_name).to_playwright_locator(self.page)
        return await locator.count()

    async def extract_table(
        self,
        selector_name: str,
        header_selector: str = "th",
        row_selector: str = "tr",
        cell_selector: str = "td",
    ) -> List[Dict[str, str]]:
        """Extrae una tabla HTML a lista de diccionarios."""
        locator = self.selector(selector_name).to_playwright_locator(self.page)
        rows = await locator.locator(row_selector).all()

        if not rows:
            return []

        # Headers
        header_cells = await rows[0].locator(header_selector).all()
        headers = [(await h.text_content() or "").strip() for h in header_cells]

        # Data rows
        data = []
        for row in rows[1:]:
            cells = await row.locator(cell_selector).all()
            values = [(await c.text_content() or "").strip() for c in cells]
            if len(values) == len(headers):
                data.append(dict(zip(headers, values)))
        return data

    # ===== Esperas avanzadas =====

    async def wait_for_selector(
        self,
        selector_name: str,
        state: str = "visible",
        timeout: Optional[float] = None,
    ) -> Locator:
        """Espera a que un selector cumpla condición."""
        locator = self.selector(selector_name).to_playwright_locator(self.page)
        await locator.wait_for(state=state, timeout=timeout or self.default_timeout)
        return locator

    async def wait_for_text(
        self,
        selector_name: str,
        text: str,
        timeout: Optional[float] = None,
    ) -> None:
        """Espera a que elemento contenga texto específico."""
        locator = self.selector(selector_name).to_playwright_locator(self.page)
        await locator.wait_for(state="visible", timeout=timeout or self.default_timeout)
        # Polling hasta que aparezca el texto
        start = asyncio.get_event_loop().time()
        max_wait = (timeout or self.default_timeout) / 1000
        while asyncio.get_event_loop().time() - start < max_wait:
            content = await locator.text_content()
            if content and text in content:
                return
            await asyncio.sleep(0.1)
        raise PlaywrightTimeoutError(f"Texto '{text}' no apareció en {selector_name}")

    async def wait_for_url(self, pattern: str, timeout: Optional[float] = None) -> None:
        """Espera a que la URL coincida con patrón."""
        await self.page.wait_for_url(pattern, timeout=timeout or self.default_timeout)

    async def wait_for_load_state(self, state: str = "networkidle", timeout: Optional[float] = None) -> None:
        """Espera estado de carga."""
        await self.page.wait_for_load_state(state, timeout=timeout or self.default_timeout)

    async def wait_for_download(self, timeout: Optional[float] = None):
        """Espera una descarga."""
        return await self.page.wait_for_event("download", timeout=timeout or self.default_timeout)

    # ===== Capturas =====

    async def screenshot(
        self,
        path: Union[str, Path],
        full_page: bool = True,
        selector_name: Optional[str] = None,
    ) -> bytes:
        """Toma screenshot (página completa o elemento)."""
        if selector_name:
            locator = self.selector(selector_name).to_playwright_locator(self.page)
            return await locator.screenshot(path=path, timeout=self.default_timeout)
        return await self.page.screenshot(path=path, full_page=full_page, timeout=self.default_timeout)

    # ===== Archivos =====

    async def upload_file(
        self,
        selector_name: str,
        file_path: Union[str, Path],
    ) -> None:
        """Sube archivo via input[type=file]."""
        locator = self.selector(selector_name).to_playwright_locator(self.page)
        await locator.set_input_files(file_path, timeout=self.default_timeout)

    # ===== JavaScript =====

    async def evaluate(self, script: str, *args) -> Any:
        """Ejecuta JavaScript en la página."""
        return await self.page.evaluate(script, *args)

    async def evaluate_handle(self, script: str, *args):
        """Ejecuta JS y retorna handle."""
        return await self.page.evaluate_handle(script, *args)

    # ===== Navegación =====

    async def go_back(self, wait_until: str = "networkidle") -> None:
        await self.page.go_back(wait_until=wait_until, timeout=self.default_timeout)

    async def go_forward(self, wait_until: str = "networkidle") -> None:
        await self.page.go_forward(wait_until=wait_until, timeout=self.default_timeout)

    async def reload(self, wait_until: str = "networkidle") -> None:
        await self.page.reload(wait_until=wait_until, timeout=self.default_timeout)

    # ===== Utilidades =====

    def get_url(self) -> str:
        return self.page.url

    def get_title(self) -> str:
        return self.page.title()