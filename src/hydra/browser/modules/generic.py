"""
Generic Website Module - Módulo genérico para cualquier sitio web.

Proporciona funcionalidad básica para sitios sin módulo específico:
- Navegación genérica
- Extracción de datos
- Formularios
- Capturas
- Acciones personalizadas via selectores
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.async_api import Page

from hydra.browser.core.page_objects import BasePageObject, Selector
from hydra.browser.artifacts import ArtifactStore
from hydra.browser.vision import VisionAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class GenericAction:
    """Acción genérica parametrizada."""
    action: str  # click, fill, hover, select, wait, navigate, screenshot, extract
    selector: Optional[str] = None
    value: Any = None
    url: Optional[str] = None
    wait_for: Optional[str] = None
    timeout: float = 10000
    options: Dict[str, Any] = None


class GenericPageObject(BasePageObject):
    """Page Object genérico que usa selectores dinámicos."""

    def _initialize_selectors(self) -> None:
        # Selectores comunes genéricos
        self.register_selector("body", Selector(css="body"))
        self.register_selector("main", Selector(css="main, [role='main']"))
        self.register_selector("button_primary", Selector(
            css="button.primary, button.btn-primary, .btn-primary",
            text="Submit",
        ))
        self.register_selector("input_text", Selector(css="input[type='text'], input:not([type])"))
        self.register_selector("input_email", Selector(css="input[type='email']"))
        self.register_selector("input_password", Selector(css="input[type='password']"))
        self.register_selector("form", Selector(css="form"))
        self.register_selector("table", Selector(css="table"))
        self.register_selector("link", Selector(css="a[href]"))

    def get_selector(self, selector_str: str) -> Selector:
        """Crea selector dinámico desde string."""
        # Soporta: css=..., xpath=..., text=..., role=...
        if selector_str.startswith("css="):
            return Selector(css=selector_str[4:])
        elif selector_str.startswith("xpath="):
            return Selector(xpath=selector_str[6:])
        elif selector_str.startswith("text="):
            return Selector(text=selector_str[5:])
        elif selector_str.startswith("role="):
            return Selector(role=selector_str[5:])
        elif selector_str.startswith("data-name="):
            return Selector(data_name=selector_str[10:])
        elif selector_str.startswith("testid="):
            return Selector(data_testid=selector_str[7:])
        else:
            # Asumir CSS
            return Selector(css=selector_str)


class GenericModule:
    """
    Módulo genérico para cualquier sitio web.

    Permite ejecutar secuencias de acciones definidas en configuración
    o realizar operaciones ad-hoc via selectores.
    """

    service_name = "generic"
    base_url = ""

    def __init__(
        self,
        browser_pool,
        session_manager,
        artifact_store: Optional[ArtifactStore] = None,
        vision_analyzer: Optional[VisionAnalyzer] = None,
        base_url: str = "",
    ):
        self.browser_pool = browser_pool
        self.session_manager = session_manager
        self.artifact_store = artifact_store
        self.vision_analyzer = vision_analyzer
        self.base_url = base_url
        self.page_object = GenericPageObject(None, base_url=base_url)

    async def execute_actions(
        self,
        page: Page,
        actions: List[GenericAction],
        artifact_store: Optional[ArtifactStore] = None,
        session=None,
    ) -> List[Dict[str, Any]]:
        """Ejecuta lista de acciones genéricas."""
        self.page_object.page = page
        results = []

        for i, action in enumerate(actions):
            try:
                result = await self._execute_action(page, action, artifact_store, session)
                results.append({
                    "step": i,
                    "action": action.action,
                    "success": True,
                    "result": result,
                })
            except Exception as e:
                logger.error(f"Error en acción {i} ({action.action}): {e}")
                results.append({
                    "step": i,
                    "action": action.action,
                    "success": False,
                    "error": str(e),
                })
                if not action.options.get("continue_on_error", False):
                    break

        return results

    async def _execute_action(
        self,
        page: Page,
        action: GenericAction,
        artifact_store: Optional[ArtifactStore],
        session,
    ) -> Any:
        """Ejecuta una acción individual."""
        selector = action.selector

        if action.action == "navigate":
            url = action.url or self.base_url
            await page.goto(url, wait_until=action.wait_for or "networkidle", timeout=action.timeout)
            return {"url": page.url}

        elif action.action == "click":
            locator = page.locator(selector) if selector else page
            await locator.click(timeout=action.timeout)
            return {"clicked": True}

        elif action.action == "double_click":
            await page.locator(selector).dblclick(timeout=action.timeout)
            return {"double_clicked": True}

        elif action.action == "hover":
            await page.locator(selector).hover(timeout=action.timeout)
            return {"hovered": True}

        elif action.action == "fill":
            await page.locator(selector).fill(str(action.value), timeout=action.timeout)
            return {"filled": True}

        elif action.action == "press":
            await page.locator(selector).press(action.value, timeout=action.timeout)
            return {"pressed": action.value}

        elif action.action == "select":
            await page.locator(selector).select_option(action.value, timeout=action.timeout)
            return {"selected": action.value}

        elif action.action == "wait":
            if selector:
                await page.locator(selector).wait_for(state="visible", timeout=action.timeout)
            elif action.wait_for:
                await page.wait_for_url(action.wait_for, timeout=action.timeout)
            else:
                await asyncio.sleep(action.timeout / 1000)
            return {"waited": True}

        elif action.action == "screenshot":
            path = action.value or f"screenshot_{datetime.utcnow().strftime('%H%M%S')}.png"
            if selector:
                content = await page.locator(selector).screenshot(path=path, type="png")
            else:
                content = await page.screenshot(path=path, full_page=True, type="png")

            if artifact_store and session:
                await artifact_store.add_artifact(
                    session, "screenshot", path,
                    tags=["screenshot", f"step_{action.step}"],
                )
            return {"screenshot": path}

        elif action.action == "extract_text":
            if selector:
                text = await page.locator(selector).text_content()
            else:
                text = await page.text_content("body")
            return {"text": text.strip() if text else ""}

        elif action.action == "extract_attribute":
            attr = action.value or "href"
            value = await page.locator(selector).get_attribute(attr)
            return {attr: value}

        elif action.action == "extract_table":
            rows = await page.locator(f"{selector} tr").all()
            data = []
            for row in rows:
                cells = await row.locator("td, th").all()
                row_data = [(await c.text_content() or "").strip() for c in cells]
                data.append(row_data)
            return {"table": data}

        elif action.action == "evaluate":
            result = await page.evaluate(action.value)
            return {"result": result}

        elif action.action == "upload":
            await page.locator(selector).set_input_files(action.value)
            return {"uploaded": True}

        elif action.action == "download":
            async with page.expect_download(timeout=action.timeout) as download_info:
                if selector:
                    await page.locator(selector).click()
            download = await download_info.value
            save_path = action.value or download.suggested_filename
            await download.save_as(save_path)
            return {"path": save_path}

        else:
            raise ValueError(f"Acción no soportada: {action.action}")

    # ===== Helpers de alto nivel =====

    async def login_form(
        self,
        page: Page,
        email_selector: str,
        password_selector: str,
        submit_selector: str,
        email: str,
        password: str,
        totp_selector: Optional[str] = None,
        totp_code: Optional[str] = None,
    ) -> bool:
        """Rellena y envía formulario de login genérico."""
        try:
            await page.locator(email_selector).fill(email)
            await page.locator(password_selector).fill(password)
            await page.locator(submit_selector).click()

            if totp_selector and totp_code:
                await page.locator(totp_selector).fill(totp_code)
                await page.locator(submit_selector).click()

            return True
        except Exception as e:
            logger.error(f"Login form falló: {e}")
            return False

    async def fill_form(
        self,
        page: Page,
        fields: Dict[str, str],
        submit_selector: Optional[str] = None,
    ) -> bool:
        """Rellena formulario genérico con diccionario selector->valor."""
        try:
            for selector, value in fields.items():
                await page.locator(selector).fill(value)
            if submit_selector:
                await page.locator(submit_selector).click()
            return True
        except Exception as e:
            logger.error(f"Fill form falló: {e}")
            return False

    async def wait_for_any(
        self,
        page: Page,
        selectors: List[str],
        timeout: float = 10000,
    ) -> Optional[str]:
        """Espera a que aparezca cualquiera de los selectores."""
        import time
        start = time.time()
        while time.time() - start < timeout / 1000:
            for sel in selectors:
                try:
                    await page.locator(sel).wait_for(state="visible", timeout=1000)
                    return sel
                except Exception:
                    continue
            await asyncio.sleep(0.1)
        return None

    async def infinite_scroll(
        self,
        page: Page,
        scroll_selector: str = "window",
        max_scrolls: int = 10,
        wait_between: float = 1000,
    ) -> int:
        """Scroll infinito genérico."""
        scrolls = 0
        last_height = 0

        for _ in range(max_scrolls):
            if scroll_selector == "window":
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                new_height = await page.evaluate("document.body.scrollHeight")
            else:
                await page.locator(scroll_selector).evaluate("el => el.scrollTop = el.scrollHeight")
                new_height = await page.locator(scroll_selector).evaluate("el => el.scrollHeight")

            if new_height == last_height:
                break
            last_height = new_height
            scrolls += 1
            await asyncio.sleep(wait_between / 1000)

        return scrolls