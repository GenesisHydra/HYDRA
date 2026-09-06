"""
Browser Pool - Gestión de múltiples contextos Chromium persistentes.

Permite reutilizar sesiones, aislar perfiles por servicio y escalar
horizontalmente manteniendo bajo consumo de recursos.
"""

import asyncio
import hashlib
import logging
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

logger = logging.getLogger(__name__)


@dataclass
class BrowserContextConfig:
    """Configuración para un contexto de navegador."""
    profile_name: str
    viewport: Dict[str, int] = field(default_factory=lambda: {"width": 1920, "height": 1080})
    user_agent: Optional[str] = None
    locale: str = "en-US"
    timezone_id: str = "UTC"
    permissions: List[str] = field(default_factory=list)
    geolocation: Optional[Dict[str, float]] = None
    color_scheme: str = "dark"
    reduced_motion: str = "reduce"
    force_headless: bool = True
    args: List[str] = field(default_factory=lambda: [
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-gpu",
    ])
    record_video: bool = False
    video_dir: Optional[Path] = None
    record_har: bool = False
    har_path: Optional[Path] = None


@dataclass
class PooledContext:
    """Contexto en el pool con metadatos."""
    context: BrowserContext
    config: BrowserContextConfig
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used: datetime = field(default_factory=datetime.utcnow)
    use_count: int = 0
    locked: bool = False
    health_check_failures: int = 0
    pages: Set[Page] = field(default_factory=set)


class BrowserPool:
    """
    Pool de contextos de navegador persistentes.

    Características:
    - Reutilización de contextos (cookies, localStorage, sesión)
    - Aislamiento por perfil/servicio
    - Health checks automáticos
    - Lifecycle management (creación, reutilización, cierre)
    - Soporte para grabación de video/HAR
    - Thread-safe para uso concurrente
    """

    def __init__(
        self,
        max_contexts: int = 10,
        max_idle_time: timedelta = timedelta(minutes=30),
        health_check_interval: timedelta = timedelta(minutes=5),
        default_config: Optional[BrowserContextConfig] = None,
        playwright: Optional[Playwright] = None,
        browser: Optional[Browser] = None,
    ):
        self.max_contexts = max_contexts
        self.max_idle_time = max_idle_time
        self.health_check_interval = health_check_interval
        self.default_config = default_config or BrowserContextConfig(profile_name="default")

        self._playwright: Optional[Playwright] = playwright
        self._browser: Optional[Browser] = browser
        self._contexts: Dict[str, PooledContext] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._health_check_task: Optional[asyncio.Task] = None
        self._owned_playwright = playwright is None
        self._owned_browser = browser is None

    async def start(self) -> None:
        """Inicializa Playwright y el navegador."""
        if self._playwright is None:
            self._playwright = await async_playwright().start()
        if self._browser is None:
            self._browser = await self._playwright.chromium.launch(
                headless=self.default_config.force_headless,
                args=self.default_config.args,
            )
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("BrowserPool iniciado")

    async def stop(self) -> None:
        """Detiene el pool y libera recursos."""
        for task in (self._cleanup_task, self._health_check_task):
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        async with self._lock:
            for pooled in self._contexts.values():
                await self._close_context(pooled)
            self._contexts.clear()

        if self._browser and self._owned_browser:
            await self._browser.close()
            self._browser = None

        if self._playwright and self._owned_playwright:
            await self._playwright.stop()
            self._playwright = None

        logger.info("BrowserPool detenido")

    @asynccontextmanager
    async def acquire(self, config: Optional[BrowserContextConfig] = None) -> BrowserContext:
        """
        Adquiere un contexto del pool (crea uno nuevo o reusa existente).

        Uso:
            async with pool.acquire(config) as context:
                page = await context.new_page()
                await page.goto("https://example.com")
        """
        pooled = await self._get_or_create_context(config or self.default_config)
        pooled.locked = True
        pooled.last_used = datetime.utcnow()
        pooled.use_count += 1

        try:
            yield pooled.context
        finally:
            pooled.locked = False
            pooled.last_used = datetime.utcnow()

    async def _get_or_create_context(self, config: BrowserContextConfig) -> PooledContext:
        """Obtiene un contexto existente compatible o crea uno nuevo."""
        async with self._lock:
            # Buscar contexto compatible (mismo perfil, no bloqueado, sano)
            for key, pooled in self._contexts.items():
                if (pooled.config.profile_name == config.profile_name
                        and not pooled.locked
                        and pooled.health_check_failures == 0):
                    logger.debug(f"Reutilizando contexto: {key}")
                    return pooled

            # Crear nuevo contexto si hay espacio
            if len(self._contexts) >= self.max_contexts:
                # Evict el menos usado recientemente
                await self._evict_lru()

            return await self._create_context(config)

    async def _create_context(self, config: BrowserContextConfig) -> PooledContext:
        """Crea un nuevo contexto de navegador."""
        if not self._browser:
            raise RuntimeError("BrowserPool no iniciado. Llama a start() primero.")

        context = await self._browser.new_context(
            viewport=config.viewport,
            user_agent=config.user_agent,
            locale=config.locale,
            timezone_id=config.timezone_id,
            permissions=config.permissions,
            geolocation=config.geolocation,
            color_scheme=config.color_scheme,
            reduced_motion=config.reduced_motion,
            record_video_dir=config.video_dir if config.record_video else None,
            record_har_path=config.har_path if config.record_har else None,
        )

        # Anti-detection: ocultar webdriver
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)

        key = self._generate_key(config)
        pooled = PooledContext(context=context, config=config)
        self._contexts[key] = pooled

        logger.info(f"Nuevo contexto creado: {key} (total: {len(self._contexts)})")
        return pooled

    async def _close_context(self, pooled: PooledContext) -> None:
        """Cierra un contexto y limpia páginas asociadas."""
        for page in pooled.pages.copy():
            try:
                await page.close()
            except Exception:
                pass
        pooled.pages.clear()

        try:
            await pooled.context.close()
        except Exception as e:
            logger.warning(f"Error cerrando contexto: {e}")

    async def _evict_lru(self) -> None:
        """Expulsa el contexto menos usado recientemente."""
        if not self._contexts:
            return

        lru_key = min(
            self._contexts.keys(),
            key=lambda k: self._contexts[k].last_used
        )
        pooled = self._contexts.pop(lru_key)
        await self._close_context(pooled)
        logger.debug(f"Contexto expulsado (LRU): {lru_key}")

    def _generate_key(self, config: BrowserContextConfig) -> str:
        """Genera clave única para la configuración."""
        config_str = f"{config.profile_name}:{config.viewport}:{config.user_agent}"
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]

    async def _cleanup_loop(self) -> None:
        """Limpia contextos inactivos periódicamente."""
        while True:
            try:
                await asyncio.sleep(self.max_idle_time.total_seconds())
                await self._cleanup_idle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error en cleanup loop: {e}")

    async def _cleanup_idle(self) -> None:
        """Cierra contextos que han estado inactivos demasiado tiempo."""
        now = datetime.utcnow()
        async with self._lock:
            to_remove = [
                key for key, pooled in self._contexts.items()
                if not pooled.locked
                and (now - pooled.last_used) > self.max_idle_time
            ]
            for key in to_remove:
                pooled = self._contexts.pop(key)
                await self._close_context(pooled)
                logger.debug(f"Contexto expirado removido: {key}")

    async def _health_check_loop(self) -> None:
        """Verifica salud de los contextos periódicamente."""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval.total_seconds())
                await self._health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error en health check: {e}")

    async def _health_check(self) -> None:
        """Verifica que los contextos respondan correctamente."""
        async with self._lock:
            for key, pooled in list(self._contexts.items()):
                if pooled.locked:
                    continue
                try:
                    page = await pooled.context.new_page()
                    await page.close()
                    pooled.health_check_failures = 0
                except Exception as e:
                    pooled.health_check_failures += 1
                    logger.warning(f"Health check falló para {key}: {e} "
                                   f"(fallos: {pooled.health_check_failures})")
                    if pooled.health_check_failures >= 3:
                        await self._close_context(pooled)
                        self._contexts.pop(key, None)
                        logger.error(f"Contexto removido por health check: {key}")

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas del pool."""
        return {
            "total_contexts": len(self._contexts),
            "max_contexts": self.max_contexts,
            "contexts": {
                key: {
                    "profile": p.config.profile_name,
                    "created": p.created_at.isoformat(),
                    "last_used": p.last_used.isoformat(),
                    "use_count": p.use_count,
                    "locked": p.locked,
                    "health_failures": p.health_check_failures,
                    "open_pages": len(p.pages),
                }
                for key, p in self._contexts.items()
            }
        }

    async def create_page(self, context: BrowserContext) -> Page:
        """Crea una página y la registra en el contexto."""
        page = await context.new_page()
        # Registrar página en el pooled context correspondiente
        for pooled in self._contexts.values():
            if pooled.context == context:
                pooled.pages.add(page)
                break
        return page

    async def close_page(self, context: BrowserContext, page: Page) -> None:
        """Cierra una página y la desregistra."""
        await page.close()
        for pooled in self._contexts.values():
            if pooled.context == context:
                pooled.pages.discard(page)
                break