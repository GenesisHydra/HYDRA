# HYDRA TradingView Automation — Arquitectura Técnica

**Versión:** 1.0
**Fecha:** 2026-09-04
**Estado:** Propuesta de arquitectura (pre-implementación)

---

## 1. Resumen Ejecutivo

Este documento define la arquitectura para **HYDRA TradingView Automation**, un subsistema que permite desarrollar, probar y mantener indicadores Pine Script de forma totalmente automática en entorno VPS headless (Ubuntu, sin escritorio gráfico, ejecución en tmux).

**Conclusión principal:** TradingView **no expone ninguna API pública oficial** para crear, compilar, validar, añadir al gráfico o publicar scripts Pine. La única vía viable y sostenible es **automatización de navegador (Chromium + Playwright)** sobre la interfaz web oficial.

---

## 2. Análisis de APIs Oficiales de TradingView

### 2.1 APIs Públicas Documentadas

| API | Propósito | ¿Sirve para Pine Automation? |
|-----|-----------|------------------------------|
| **Charting Library** | Incrustar gráficos TradingView en tu web con tus datos | No — solo renderizado, sin Pine Editor |
| **Lightweight Charts™** | Librería ligera de gráficos financieros (canvas) | No — sin Pine Script |
| **Broker REST API** | Integración de brokers (órdenes, posiciones, cuenta) | No — sin Pine Script |
| **Study Templates API** (`/api/v1/study-templates`) | Lista plantillas predefinidas de indicadores | Solo lectura, no permite crear/compilar |

### 2.2 APIs Privadas / Internas (NO USAR)

TradingView usa internamente endpoints no documentados para su aplicación web (ej. `https://www.tradingview.com/api/v1/pine/...`, `script-editor`, `chart-layout`, etc.). **Estos NO son APIs públicas**:

- Requieren autenticación compleja (cookies, tokens CSRF, headers `x-tradingview-*`)
- Cambian sin previo aviso entre releases
- Están protegidos por WAF / rate-limiting agresivo
- Su uso viola los Términos de Servicio de TradingView
- No hay soporte, documentación ni SLA

**Decisión de arquitectura:** **NO se utilizarán endpoints privados**. Toda la automatización se hará mediante interacción real con la UI web (Playwright), igual que un usuario humano.

---

## 3. Arquitectura Propuesta

### 3.1 Diagrama de Alto Nivel

```
┌─────────────────────────────────────────────────────────────────┐
│                      HYDRA TRADINGVIEW AUTOMATION               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │  Orchestrator│───▶│  Browser Pool│───▶│  TradingView Web │  │
│  │   (Python)   │    │  (Playwright)│    │  (Chromium Headless)│
│  └──────────────┘    └──────────────┘    └──────────────────┘  │
│        │                   │                     │              │
│        ▼                   ▼                     ▼              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │  Task Queue  │    │  Session Mgmt│    │  Pine Editor     │  │
│  │  (Redis/SQL) │    │  (Cookies/   │    │  • Load script   │  │
│  └──────────────┘    │   LocalStorage)    │  • Compile       │  │
│                      └──────────────┘    │  • Add to chart  │  │
│                                           │  • Capture errors│  │
│                                           │  • Screenshot    │  │
│                                           └──────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Componentes

| Componente | Tecnología | Responsabilidad |
|------------|------------|-----------------|
| **TVAutomationOrchestrator** | Python 3.11+ | Orquesta tareas, gestiona cola, reintentos, timeouts |
| **PlaywrightBrowserPool** | Playwright (Python) | Pool de contextos Chromium persistentes, reuse de sesiones |
| **TVSessionManager** | Python + Playwright | Login, persistencia de cookies, 2FA, renovación de sesión |
| **PineEditorController** | Playwright (Page Object) | Abrir editor, cargar código, compilar, añadir al gráfico, capturar errores |
| **ValidationReporter** | Python | Genera informe JSON/HTML con: estado compilación, errores, screenshots, métricas |
| **ArtifactStore** | Filesystem / S3-compatible | Guarda .pine, screenshots, logs, reportes |

### 3.3 Flujo de Trabajo Principal

```
1. ORCHESTRATOR recibe tarea: validar genesis_vwap.pine
2. BROWSER_POOL obtiene página autenticada (reuse o login fresco)
3. PINE_EDITOR_CONTROLLER:
   a. Navega a /chart/ → Pine Editor tab
   b. Limpia editor → pega contenido genesis_vwap.pine
   c. Click "Add to chart" / "Save"
   d. Espera compilación → captura:
      - ¿Compilación exitosa? (sí/no)
      - Errores/warnings (texto + línea)
      - Screenshot del gráfico con indicador
      - Screenshot del panel de errores si falla
4. VALIDATION_REPORTER genera informe estructurado
5. ARTIFACT_STORE persiste todo
6. BROWSER_POOL devuelve página al pool (no cierra)
```

---

## 4. Detalles de Implementación Críticos

### 4.1 Autenticación y Persistencia de Sesión

- **Login:** Usuario/contraseña + 2FA (TOTP) → guardar `localStorage`, `cookies`, `sessionStorage` en disco cifrado
- **Reutilización:** Cargar estado guardado → evita login repetido y desafíos de captcha
- **Renovación:** Detectar expiración (redirect a login) → re-login automático
- **Seguridad:** Credenciales en variables de entorno / secret manager (NO en repo)

### 4.2 Selectores Robustos (Page Object Pattern)

TradingView usa clases CSS generadas (ej. `.tv-pine-editor__textarea`, `button[data-name="add-to-chart"]`). Estrategia:

- Usar `data-name`, `aria-label`, `role`, `text=` selectores semánticos
- Fallback a XPath basado en estructura DOM estable
- Registrar selectores en config versionado para adaptarse a cambios UI

### 4.3 Manejo de Errores de Compilación

TradingView muestra errores en:
1. **Toast/notification** superior (transitorio)
2. **Panel inferior** "Pine Editor - Errors" (persistente)
3. **Inline** en el editor (línea roja)

El controlador debe:
- Esperar `networkidle` tras click "Add to chart"
- Buscar panel de errores → extraer `textContent`
- Parsear: línea, columna, código error (ej. `CE10101`), mensaje
- Si no hay panel de errores → asumir éxito

### 4.4 Capturas de Pantalla

- **Full page** del gráfico con indicador aplicado (viewport 1920x1080)
- **Viewport only** del panel de errores (si falla)
- **Element screenshot** del Pine Editor (código cargado)
- Formato: PNG, nombre con timestamp + hash del script

### 4.5 Headless en VPS (Ubuntu + tmux)

```bash
# Dependencias sistema
apt-get update && apt-get install -y \
  libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
  libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
  libxrandr2 libgbm1 libasound2 libatspi2.0-0

# Playwright instala su propio Chromium
playwright install chromium
playwright install-deps chromium
```

Ejecución en tmux:
```bash
tmux new-session -d -s hydra-tv 'python -m hydra.tv_automation run --script genesis_vwap.pine'
```

---

## 5. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Cambios en UI de TradingView (selectores rotos) | Alta | Alto | Page Object + tests de regresión visual semanales; alertas en CI |
| Captcha / desafíos anti-bot en login | Media | Alto | Sesiones persistentes; rotación de User-Agent; delays humanos; resolver 2FA via TOTP |
| Rate limiting / ban de IP | Media | Medio | Pool de proxies residenciales (opcional); backoff exponencial; una sesión por IP |
| Tiempo de carga variable (red, CDN) | Alta | Bajo | Timeouts generosos (60-120s); `wait_for_load_state('networkidle')` |
| TradingView bloquea automatización (ToS) | Baja-Media | Crítico | Uso legítimo: desarrollo propio, no scraping masivo; respetar `robots.txt`; límites de frecuencia |
| Fallo de 2FA (dispositivo no disponible) | Baja | Alto | Backup codes almacenados; alerta a operador humano |

---

## 6. Limitaciones Conocidas

1. **No hay API oficial** → dependencia total de UI web (frágil ante rediseños)
2. **Sesión única por usuario** → concurrencia limitada (1 browser context por cuenta)
3. **2FA obligatorio** → requiere gestión segura de secretos TOTP
4. **Sin sandbox real de Pine** → la compilación ocurre en servidor TV; no podemos compilar offline
5. **No acceso a AST / análisis estático** → solo errores que TV devuelve en UI
6. **Coste de recursos** → Chromium headless ~300-500 MB RAM por contexto
7. **Latencia** → ciclo completo ~30-90 segundos por script

---

## 7. Ventajas del Enfoque Browser Automation

| Ventaja | Descripción |
|---------|-------------|
| **Fidelidad 100%** | Mismo entorno que usuario real: misma compilación, mismos errores, mismas features |
| **Cobertura completa** | Acceso a todo lo que hace el usuario: Pine Editor, gráfico, alertas, publicación, backtesting |
| **Sin ingeniería inversa** | No hay que reverse-engineer APIs privadas ni mantener clientes HTTP frágiles |
| **Actualizaciones automáticas** | Al usar UI real, nuevas features de Pine (v6, v7...) funcionan sin cambios de código |
| **Depuración visual** | Screenshots y videos de cada ejecución para diagnóstico |
| **Compatible con HYDRA Browser** | Reusa infraestructura Playwright/Chromium ya existente en HYDRA |

---

## 8. Estimación de Recursos

| Recurso | Estimación |
|---------|------------|
| **Desarrollo inicial** | 3-5 días (Orchestrator + Page Objects + Session Manager + Reporter) |
| **RAM por worker** | 400-600 MB (Chromium + Python) |
| **CPU** | Bajo (mayormente I/O wait) |
| **Disco** | ~50 MB base + ~5 MB por ejecución (screenshots, logs) |
| **Red** | ~10-20 MB por ejecución (carga TV + assets) |
| **Concurrencia recomendada** | 1-2 workers por cuenta TV (evitar rate-limit) |
| **Mantenimiento** | ~2 h/mes (actualizar selectores si TV cambia UI) |

---

## 9. Plan de Implementación (Fases)

### Fase 0 — Preparación (0.5 días)
- [ ] Crear repo `hydra-tv-automation` dentro de HYDRA
- [ ] Añadir dependencias: `playwright`, `pytest-playwright`, `pydantic`, `pyyaml`
- [ ] Configurar `playwright install chromium --with-deps` en Dockerfile/CI

### Fase 1 — Núcleo de Navegación (1.5 días)
- [ ] `BrowserPool`: contexto persistente, lifecycle, health-check
- [ ] `TVSessionManager`: login, 2FA (TOTP via `pyotp`), guardado/carga estado
- [ ] Tests: login exitoso, reutilización de sesión, expiración

### Fase 2 — Controlador Pine Editor (1.5 días)
- [ ] `PineEditorController` (Page Object):
  - `open_editor()`
  - `load_script(content: str)`
  - `click_add_to_chart()`
  - `wait_for_compilation(timeout=60)`
  - `get_compilation_errors() -> List[CompilationError]`
  - `screenshot_chart(path)`
  - `screenshot_errors(path)`
- [ ] Tests con `genesis_vwap.pine` (éxito) y script con error sintáctico (fallo)

### Fase 3 — Orquestación y Reportes (1 día)
- [ ] `TVAutomationOrchestrator`: cola tareas, reintentos, timeouts globales
- [ ] `ValidationReporter`: genera `validation_report.json` + `validation_report.html`
- [ ] Integración con `ArtifactStore` (filesystem local + opcional S3)

### Fase 4 — Integración HYDRA (0.5 días)
- [ ] CLI entrypoint: `hydra-tv validate --script genesis_vwap.pine`
- [ ] Configuración vía `config/tv_automation.yaml` (credenciales, timeouts, paths)
- [ ] Logs estructurados (JSON) compatibles con stack observabilidad HYDRA

### Fase 5 — Hardening y CI (1 día)
- [ ] Tests E2E en CI (headless)
- [ ] Monitor de salud: alerta si login falla >3 veces seguidas
- [ ] Documentación de operación (runbook)
- [ ] Prueba de carga: 10 validaciones secuenciales

---

## 10. Criterios de Aceptación (Definition of Done)

Un script Pine se considera **validado automáticamente** cuando el sistema produce un informe con:

```json
{
  "script": "genesis_vwap.pine",
  "timestamp": "2026-09-04T16:30:00Z",
  "status": "SUCCESS",  // o "COMPILATION_ERROR", "RUNTIME_ERROR", "TIMEOUT"
  "compilation": {
    "success": true,
    "errors": [],
    "warnings": []
  },
  "screenshots": {
    "chart": "artifacts/genesis_vwap_20260904_163000_chart.png",
    "editor": "artifacts/genesis_vwap_20260904_163000_editor.png"
  },
  "metrics": {
    "total_duration_ms": 45200,
    "login_duration_ms": 12000,
    "compilation_duration_ms": 8000
  }
}
```

---

## 11. Referencias

- [Pine Script v6 User Manual](https://www.tradingview.com/pine-script-docs/)
- [TradingView Charting Library Docs](https://www.tradingview.com/charting-library-docs/)
- [Playwright Python Docs](https://playwright.dev/python/)
- [TradingView REST API for Brokers](https://www.tradingview.com/rest-api-spec/)
- [HYDRA Browser Infrastructure](../browser/)

---

## 12. Decisiones Pendientes (Para Validación)

1. **Cuenta TradingView dedicada** vs. cuenta compartida: ¿Usar una cuenta bot exclusiva para HYDRA?
2. **Proxy residencial**: ¿Necesario desde día 1 o solo si hay rate-limiting?
3. **Publicación automática**: ¿Incluir en MVP o solo validación local? (Publicar requiere más pasos UI y revisión manual TV)
4. **Backtesting automático**: ¿Alcance fase 1 o fase 2?
5. **Notificaciones**: ¿Webhook a Slack/Telegram al finalizar validación?

---

**Fin del documento — Pendiente revisión y aprobación antes de implementar.**