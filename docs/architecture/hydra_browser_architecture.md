# HYDRA Browser — Arquitectura de Infraestructura de Automatización Web

**Versión:** 1.0
**Fecha:** 2026-09-04
**Estado:** v1.0 — Infraestructura Estable

---

## 1. Resumen Ejecutivo

**HYDRA Browser** es la infraestructura unificada de automatización web para el ecosistema HYDRA.

Es un **componente de infraestructura puro** que proporciona capacidades genéricas de automatización de navegador. **No contiene integraciones con servicios externos** (Gmail, YouTube, LinkedIn, X, GitHub, TradingView, etc.).

Todas las integraciones con servicios externos viven en paquetes separados:
- `src/hydra/tradingview/` — Automatización TradingView
- `src/hydra/google/` — Autenticación y APIs Google
- `src/hydra/youtube/` — YouTube
- `src/hydra/linkedin/` — LinkedIn
- `src/hydra/x/` — X (Twitter)
- `src/hydra/github/` — GitHub
- `src/hydra/fundednext/` — FundedNext
- `src/hydra/gomining/` — GoMining
- etc.

**Principio clave:** *HYDRA Browser expone una API genérica de automatización (BrowserManager). Los conectores de servicios externos son paquetes independientes que consumen esta API a través de una interfaz común (BaseConnector).*

---

## 2. Arquitectura General (Diagrama de Capas)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AGENTES HYDRA                                   │
│  (Mail, Trading, Vault, Design, Skills, ARGO, etc.)                         │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │ MCP (Model Context Protocol)
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         HYDRA BROWSER MANAGER                                │
│                    (Único Punto de Entrada Público)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐  │
│  │   SESSION    │ │  BROWSER     │ │  ARTIFACT    │ │   VALIDATION     │  │
│  │   MANAGER    │ │    POOL      │ │   STORE      │ │   ENGINE         │  │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────────┘  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐  │
│  │   VISION     │ │  RECORDER    │ │  CONNECTOR   │ │  HEALTH MONITOR  │  │
│  │  (OCR+DOM)   │ │   (VIDEO)    │ │  REGISTRY    │ │                  │  │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    CLUSTER COORDINATOR (Local/Distribuido)           │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │ BrowserManager.execute_capability()
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      CONECTORES EXTERNOS (Paquetes Independientes)          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  src/hydra/tradingview/     → BaseConnector + TradingView logic             │
│  src/hydra/google/          → BaseConnector + Google OAuth + APIs           │
│  src/hydra/youtube/         → BaseConnector + YouTube API                   │
│  src/hydra/linkedin/        → BaseConnector + LinkedIn automation           │
│  src/hydra/x/               → BaseConnector + X/Twitter automation          │
│  src/hydra/github/          → BaseConnector + GitHub API                    │
│  src/hydra/fundednext/      → BaseConnector + FundedNext dashboard          │
│  src/hydra/gomining/        → BaseConnector + GoMining dashboard            │
│  ...                                                                       │
│                                                                              │
│  TODOS implementan: BaseConnector                                           │
│  - connect() → login() → health_check() → execute() → close()              │
│  - Declaran capacidades via ConnectorCapabilities                           │
│  - Se auto-registran en ConnectorRegistry                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CHROMIUM HEADLESS (Playwright)                      │
│                    (Gestionado por BrowserPool)                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Separación de Responsabilidades

### ✅ HYDRA Browser (Infraestructura) — `src/hydra/browser/`

| Componente | Responsabilidad |
|------------|-----------------|
| **BrowserManager** | Único punto de entrada público para conectores |
| **BrowserPool** | Múltiples contextos Chromium persistentes, health checks, LRU |
| **SessionManager** | Perfiles cifrados por servicio (cookies, localStorage, sessionStorage, permisos) |
| **BrowserActions** | API alto nivel: goto, click, fill, screenshot, wait_*, evaluate, vision |
| **Vision** | OCR (EasyOCR/Tesseract) + fusión DOM para estados visuales |
| **Recorder** | Grabación video opcional con metadatos |
| **ArtifactStore** | Persistencia estructurada (screenshots, videos, logs, reportes, scripts) |
| **ValidationEngine** | Ciclo genérico compile-fix (delega compilación real a módulos) |
| **ConnectorRegistry** | Auto-registro, descubrimiento, instanciación lazy de conectores |
| **HealthMonitor** | Métricas, alertas, Prometheus export, dashboards |
| **Cluster Coordinator** | Interfaces preparadas para cluster distribuido (modo local actual) |

### ❌ FUERA de HYDRA Browser — Paquetes Independientes `src/hydra/<servicio>/`

| Servicio | Paquete | Responsabilidad |
|----------|---------|-----------------|
| TradingView | `src/hydra/tradingview/` | Login, Pine Editor, compilación Pine, screenshots |
| Google | `src/hydra/google/` | OAuth 2.0 (Installed App + PKCE), Gmail, Drive, Calendar |
| YouTube | `src/hydra/youtube/` | Upload video, thumbnails, playlists, analytics |
| LinkedIn | `src/hydra/linkedin/` | Posts, imágenes, mensajes, networking |
| X/Twitter | `src/hydra/x/` | Tweets, DMs, scheduling, analytics |
| GitHub | `src/hydra/github/` | Issues, PRs, Actions, repos |
| FundedNext | `src/hydra/fundednext/` | Dashboard, challenges, trading |
| GoMining | `src/hydra/gomining/` | Dashboard, mining ops |

---

## 4. Interfaz Común: BaseConnector

Todos los conectores implementan `BaseConnector` con ciclo de vida estándar:

```python
class BaseConnector(ABC):
    # Ciclo de vida obligatorio
    async def connect(self, browser_manager) -> bool
    async def login(self, credentials) -> bool
    async def health_check(self) -> HealthStatus
    async def execute(self, capability: Capability, params) -> ExecutionResult
    async def close(self) -> bool
    
    # Capacidades declarativas
    @property
    @abstractmethod
    def capabilities(self) -> ConnectorCapabilities
```

### Capacidades Estándar (`Capability` enum)

```python
class Capability(Enum):
    # Auth
    LOGIN = "login"
    LOGOUT = "logout"
    HEALTH_CHECK = "health_check"
    
    # Genéricas
    NAVIGATE = "navigate"
    SCREENSHOT = "screenshot"
    EXTRACT_TEXT = "extract_text"
    EXTRACT_TABLE = "extract_table"
    UPLOAD_FILE = "upload_file"
    DOWNLOAD_FILE = "download_file"
    FILL_FORM = "fill_form"
    CLICK = "click"
    WAIT_FOR = "wait_for"
    
    # Específicas (declaradas por cada conector)
    COMPILE_PINE = "compile_pine"      # TradingView
    UPLOAD_VIDEO = "upload_video"      # YouTube
    PUBLISH_POST = "publish_post"      # LinkedIn/X
    CREATE_ISSUE = "create_issue"      # GitHub
    # ... etc.
```

---

## 5. Flujo de Ejecución: BrowserManager → Connector → Servicio

```
┌─────────────┐     1. register_connector()     ┌──────────────────┐
│   AGENTE    │ ───────────────────────────────▶ │ ConnectorRegistry │
│  (Trading)  │                                  │  (auto-discovery) │
└─────────────┘                                  └────────┬─────────┘
                                                           │
                                                           ▼
┌─────────────┐     2. execute_capability()      ┌──────────────────┐
│   AGENTE    │ ───────────────────────────────▶ │  BrowserManager  │
│  (Trading)  │  capability=COMPILE_PINE         │  (entry point)   │
└─────────────┘  params={script, name}           └────────┬─────────┘
                                                          │
                         3. get_or_create_connector()     ▼
                                                  ┌──────────────────┐
                                                  │ TradingViewConnector│
                                                  │ (BaseConnector)   │
                                                  └────────┬─────────┘
                                                           │
                                       4. execute(COMPILE_PINE)  ▼
                                                  ┌──────────────────┐
                                                  │ BrowserManager   │
                                                  │ .session()       │
                                                  └────────┬─────────┘
                                                           │
                                        5. BrowserActions  ▼
                                                  ┌──────────────────┐
                                                  │ TradingViewChart │
                                                  │ Page Object      │
                                                  └────────┬─────────┘
                                                           │
                                        6. Playwright API  ▼
                                                  ┌──────────────────┐
                                                  │ Chromium Headless │
                                                  └──────────────────┘
```

---

## 6. Capability System — Declarativo y Extensible

Cada conector declara sus capacidades:

```python
from hydra.browser.connectors import Capability, ConnectorCapabilities, get_capabilities

# Predefinido para TradingView
capabilities = get_capabilities("tradingview")
# {LOGIN, LOGOUT, HEALTH_CHECK, COMPILE_PINE, CHART_NAVIGATION, 
#  PINE_EDITOR, SCREENSHOT, EXTRACT_TEXT, BROWSER_ACTIONS}

# Uso dinámico
if browser_manager.connector_supports("tradingview", Capability.COMPILE_PINE):
    result = await browser_manager.execute_capability(
        "tradingview",
        Capability.COMPILE_PINE,
        {"script": "//@version=6\nindicator(...)", "script_name": "test.pine"}
    )
```

**Ventajas:**
- BrowserManager no conoce lógica de TradingView
- Nuevas capacidades se añaden sin tocar el core
- Rate limits, timeouts, params declarados en `CapabilitySpec`

---

## 7. ConnectorRegistry — Auto-Registro y Descubrimiento

```python
# Registro manual
registry.register(
    name="miservicio",
    connector_class=MiServicioConnector,
    capabilities=MY_CAPABILITIES,
)

# Auto-descubrimiento (busca módulos con CONNECTOR_CLASS)
registry.discover("hydra")

# Decorador para registro automático
@connector("miservicio", capabilities=MY_CAPABILITIES)
class MiServicioConnector(BaseConnector):
    ...
```

---

## 8. Health Monitoring Unificado

```python
monitor = HealthMonitor(registry, check_interval_seconds=30)
await monitor.start()

# Métricas en tiempo real
health = monitor.get_system_health()
# SystemHealth(healthy_connectors=5, degraded=0, down=0, ...)

# Prometheus export
prometheus_metrics = monitor.get_prometheus_metrics()
# hydra_connector_state{connector="tradingview"} 2
# hydra_connector_success_rate{connector="tradingview"} 0.95
# ...

# Alertas
monitor.add_alert_handler(slack_alert_handler(webhook_url))
```

---

## 8. Cluster-Ready Interfaces (Preparado para Futuro)

Arquitectura diseñada para migración a cluster distribuido sin breaking changes:

```python
# Interfaces (cluster.py)
IClusterCoordinator    # Coordinador (uno solo)
IClusterWorker         # Workers (múltiples)
ITaskQueue             # Cola distribuida

# Modo actual: Local (single-node)
coordinator = create_cluster_coordinator(ClusterMode.LOCAL, browser_manager)

# Futuro: Distribuido
coordinator = create_cluster_coordinator(ClusterMode.DISTRIBUTED, browser_manager)
```

**Migración futura sin breaking changes:**
- Conectores usan `browser_manager.execute_capability()` → transparente
- `LocalClusterCoordinator` implementa misma interfaz que distribuido
- Solo cambia factory `create_cluster_coordinator()`

---

## 9. Uso Básico

### 9.1 Inicialización Core

```python
from hydra.browser import create_browser_manager
from pathlib import Path

browser = create_browser_manager(
    profiles_dir=Path("./data/browser_profiles"),
    artifacts_dir=Path("./data/artifacts"),
    recordings_dir=Path("./data/recordings"),
    vision_cache_dir=Path("./data/vision_cache"),
)
await browser.start()

# Registrar conectores (auto-discovery o manual)
# browser.register_connector("tradingview", TradingViewConnector, capabilities)

# Los conectores se auto-registran al importarse
import hydra.tradingview  # Se auto-registra

await browser.stop()
```

### 9.2 Uso desde Agente (vía MCP o directo)

```python
# Opción A: MCP (recomendado para agentes)
mcp = browser.create_mcp()
mcp.register_agent("hydra_trading", {"module": "tradingview"})

response = await mcp.handle_request(MCPRequest(
    action="compile_pine",
    params={"script": "//@version=6\nindicator(...)", "script_name": "test.pine"},
    request_id="req_001",
    agent_name="hydra_trading",
))

# Opción B: API Directa (para conectores/scripts)
result = await browser.execute_capability(
    "tradingview",
    Capability.COMPILE_PINE,
    {"script": "//@version=6\nindicator(...)", "script_name": "test.pine"}
)
```

### 9.3 Ciclo Compile-Fix Automático

```python
# Registrar módulo de validación
browser.register_validation_module("tradingview", tradingview_module)

# Ciclo automático
async with browser.validate(script, "genesis_vwap.pine", "tradingview") as report:
    # report.status == ValidationStatus.SUCCESS
    pass
```

---

## 10. Seguridad y Mejores Prácticas

### 10.1 Credenciales
- Variables de entorno / Secret Manager (Vault, AWS Secrets Manager)
- `HYDRA_BROWSER_MASTER_KEY` para cifrado de perfiles
- TOTP secrets en Secret Manager
- Rotación periódica de claves

### 10.2 Rate Limiting & Anti-Bot
- Un contexto por cuenta de servicio
- Delays configurables, User-Agent rotation
- Proxy residencial para alta concurrencia (futuro)

### 10.3 Cumplimiento ToS
- Solo automatización de **propias cuentas y scripts**
- No scraping masivo ni crawling
- Respeto a `robots.txt` y rate limits
- Una sesión por IP/cuenta

---

## 11. Roadmap

### v1.1 — Browser API Estable ✅
- [x] BrowserManager como único entry point
- [x] BaseConnector + ciclo de vida estándar
- [x] Capability system declarativo
- [x] ConnectorRegistry con auto-discovery
- [x] HealthMonitor con Prometheus/alertas
- [x] Cluster-ready interfaces (modo local)
- [x] TradingView connector migrado

### v1.2 — Conectores Clave
- [ ] Google Auth (`src/hydra/google/`) — lib común OAuth 2.0 + PKCE + Vault
- [ ] YouTube (`src/hydra/youtube/`) — upload, analytics
- [ ] LinkedIn (`src/hydra/linkedin/`) — posts, networking
- [ ] X/Twitter (`src/hydra/x/`) — tweets, DMs
- [ ] GitHub (`src/hydra/github/`) — issues, PRs, Actions
- [ ] FundedNext (`src/hydra/fundednext/`) — dashboard
- [ ] GoMining (`src/hydra/gomining/`) — dashboard

### v2.0 — Cluster Distribuido
- [ ] Coordinador distribuido (Redis/etcd)
- [ ] Workers en múltiples VPS
- [ ] Auto-scaling basado en cola
- [ ] Visual regression testing
- [ ] Auto-healing selectors (ML)

---

## 12. Referencias

- [Playwright Python Docs](https://playwright.dev/python/)
- [Pine Script v6 Manual](https://www.tradingview.com/pine-script-docs/)
- [Fernet Spec](https://github.com/fernet/spec)
- [EasyOCR](https://github.com/JaidedAI/EasyOCR)
- [Prometheus Exposition Format](https://prometheus.io/docs/instrumenting/exposition_formats/)
- [HYDRA Architecture](../architecture/)

---

**Fin del documento — HYDRA Browser v1.0: Infraestructura estable, extensible y lista para producción.**