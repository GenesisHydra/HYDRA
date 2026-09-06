# TradingView Automation

Conector externo para automatización de TradingView usando HYDRA Browser como backend.

## Instalación

```bash
# Desde el root de HYDRA
pip install -e ./src/hydra/tradingview
```

## Uso Básico

```python
import asyncio
from pathlib import Path

from hydra.browser import create_browser_manager
from hydra.tradingview import create_tradingview_automation

async def main():
    # Inicializar BrowserManager
    browser = create_browser_manager(
        profiles_dir=Path("./data/browser_profiles"),
        artifacts_dir=Path("./data/artifacts"),
        recordings_dir=Path("./data/recordings"),
    )
    await browser.start()

    # Crear automatización TradingView
    tv = await create_tradingview_automation(
        browser_manager=browser,
        email="tu@email.com",
        password="tu_password",
        totp_secret="JBSWY3DPEHPK3PXP",  # base32 secret para 2FA
        artifact_store=browser.artifact_store,
        vision_analyzer=browser.vision_analyzer,
    )

    # Compilar script Pine
    script = Path("genesis_vwap.pine").read_text()
    result = await tv.compile_pine(script, "genesis_vwap.pine")

    print(f"Compilación: {'EXITOSA' if result.success else 'FALLIDA'}")
    if result.errors:
        for err in result.errors:
            print(f"  L{err.line}: {err.code} - {err.message}")

    # Ciclo automático con Coding Agent
    # result = await tv.validate_with_fix_cycle(script, "genesis_vwap.pine", coder_agent)

    await browser.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

## Variables de Entorno Requeridas

```bash
export HYDRA_BROWSER_MASTER_KEY="clave-secreta-32-bytes-minimo"
```

## Arquitectura

```
src/hydra/tradingview/
├── __init__.py          # TradingViewAutomation, TradingViewConfig
├── auth.py              # Login + 2FA TOTP
├── pine_editor.py       # Controlador Pine Editor
├── compiler.py          # Compilación real + captura errores
└── validation.py        # Ciclo compile-fix con Coding Agent
```

## Responsabilidades

✅ Login TradingView (email/password + 2FA TOTP)
✅ Pine Editor (cargar script via Monaco, click Add to chart)
✅ Captura errores compilación (panel UI + Vision fallback)
✅ Parseo estructurado errores (CE10101, CW10003, RE10139, etc.)
✅ Screenshots gráfico + panel errores
✅ Ciclo compile-fix automático con Coding Agent

❌ NO: Browser pool, session manager, vision, artifacts (usa HYDRA Browser)
❌ NO: OAuth Google (usa src/hydra/google/auth.py)
❌ NO: Publicación scripts (futuro)
❌ NO: Backtesting (futuro)