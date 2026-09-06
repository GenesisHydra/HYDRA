#!/usr/bin/env python3
"""
HYDRA Browser - Script de validación rápida.

Verifica que la estructura del módulo sea correcta y las importaciones funcionen.
"""

import sys
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def test_imports():
    """Testea importaciones principales."""
    print("🔍 Testing imports...")

    try:
        from hydra.browser import (
            BrowserPool,
            BrowserContextConfig,
            SessionManager,
            EncryptedProfile,
            BasePageObject,
            BrowserActions,
            HydraBrowserMCP,
            ValidationEngine,
            ArtifactStore,
        )
        print("  ✅ Core imports OK")
    except ImportError as e:
        print(f"  ❌ Core imports failed: {e}")
        return False

    try:
        from hydra.browser.core.browser_pool import BrowserPool as BP, BrowserContextConfig as BCC
        from hydra.browser.core.session_manager import SessionManager as SM, EncryptedProfile as EP
        from hydra.browser.core.page_objects import BasePageObject as BPO, Selector, WaitConfig
        from hydra.browser.core.actions import BrowserActions as BA, ActionResult
        from hydra.browser.mcp.interface import HydraBrowserMCP as HBM, MCPRequest, MCPResponse
        from hydra.browser.validation.engine import ValidationEngine as VE, CompilationError, CompilationResult
        from hydra.browser.artifacts.store import ArtifactStore as AS, Artifact, SessionArtifacts
        from hydra.browser.vision import VisionAnalyzer, OCRBackend, TesseractOCR, EasyOCRBackend, create_vision_analyzer
        from hydra.browser.recorder import VideoRecorder, RecordingConfig, RecordingMetadata
        from hydra.browser.modules import TradingViewModule, GenericModule, GenericAction, create_module, get_module_class
        print("  ✅ Submodule imports OK")
    except ImportError as e:
        print(f"  ❌ Submodule imports failed: {e}")
        return False

    try:
        from hydra.browser.modules.tradingview import (
            TradingViewLoginPage,
            TradingViewChartPage,
            TradingViewModule as TVM2,
        )
        print("  ✅ TradingView module imports OK")
    except ImportError as e:
        print(f"  ❌ TradingView imports failed: {e}")
        return False

    try:
        from hydra.browser.modules.generic import GenericModule as GM2, GenericAction as GA2
        print("  ✅ Generic module imports OK")
    except ImportError as e:
        print(f"  ❌ Generic imports failed: {e}")
        return False

    return True


def test_instantiation():
    """Testea instanciación básica (sin browser real)."""
    print("\n🔧 Testing instantiation...")

    try:
        from hydra.browser.core.browser_pool import BrowserPool, BrowserContextConfig
        config = BrowserContextConfig(profile_name="test")
        print(f"  ✅ BrowserContextConfig: {config.profile_name}")
    except Exception as e:
        print(f"  ❌ BrowserContextConfig failed: {e}")
        return False

    try:
        from hydra.browser.core.session_manager import EncryptedProfile
        profile = EncryptedProfile(service_name="test")
        print(f"  ✅ EncryptedProfile: {profile.service_name}")
    except Exception as e:
        print(f"  ❌ EncryptedProfile failed: {e}")
        return False

    try:
        from hydra.browser.core.page_objects import Selector
        sel = Selector(data_name="test", css=".test", text="Click me")
        print(f"  ✅ Selector: {sel}")
    except Exception as e:
        print(f"  ❌ Selector failed: {e}")
        return False

    try:
        from hydra.browser.validation.engine import CompilationError, ErrorType
        err = CompilationError(
            line=10, column=5,
            message="Test error",
            code="CE10101",
            severity="error",
            error_type=ErrorType.SYNTAX,
        )
        print(f"  ✅ CompilationError: {err.code} L{err.line}")
    except Exception as e:
        print(f"  ❌ CompilationError failed: {e}")
        return False

    try:
        from hydra.browser.modules import GenericAction
        action = GenericAction(action="click", selector="button", value=None)
        print(f"  ✅ GenericAction: {action.action}")
    except Exception as e:
        print(f"  ❌ GenericAction failed: {e}")
        return False

    return True


def test_error_parser():
    """Testea parser de errores Pine."""
    print("\n📝 Testing Pine error parser...")

    from hydra.browser.validation.engine import PineErrorParser, ErrorType

    test_errors = """
    line 10: Variable 'x' not defined (CE10101)
    line 25, column 3: Type mismatch: 'series float' -> 'series int' (CE10117)
    Warning: Unused variable 'y' (CW10003)
    Runtime error: Division by zero (RE10139)
    """

    errors = PineErrorParser.parse_errors(test_errors)
    warnings = PineErrorParser.parse_warnings(test_errors)

    print(f"  Parsed {len(errors)} errors, {len(warnings)} warnings")

    for err in errors:
        print(f"  • L{err.line}: {err.code} ({err.error_type.value}) - {err.message}")

    for warn in warnings:
        print(f"  • Warning: {warn.code} - {warn.message}")

    # Verificar parseo correcto
    assert len(errors) == 3, f"Expected 3 errors, got {len(errors)}"
    assert len(warnings) == 1, f"Expected 1 warning, got {len(warnings)}"
    assert errors[0].code == "CE10101"
    assert errors[1].code == "CE10117"
    assert errors[2].code == "RE10139"
    assert warnings[0].code == "CW10003"
    assert errors[0].error_type == ErrorType.SYNTAX
    assert errors[2].error_type == ErrorType.RUNTIME
    assert warnings[0].error_type == ErrorType.WARNING

    print("  ✅ Error parser working correctly")
    return True


def test_module_registry():
    """Testea registro de módulos."""
    print("\n📦 Testing module registry...")

    from hydra.browser.modules import (
        MODULES, PLANNED_MODULES, get_module_class, create_module
    )

    print(f"  Implemented modules: {list(MODULES.keys())}")
    print(f"  Planned modules: {list(PLANNED_MODULES.keys())}")

    # Test get_module_class
    tv_class = get_module_class("tradingview")
    assert tv_class.__name__ == "TradingViewModule"
    print(f"  ✅ get_module_class('tradingview') -> {tv_class.__name__}")

    gen_class = get_module_class("generic")
    assert gen_class.__name__ == "GenericModule"
    print(f"  ✅ get_module_class('generic') -> {gen_class.__name__}")

    # Test error for unknown
    try:
        get_module_class("unknown")
        print("  ❌ Should have raised ValueError")
        return False
    except ValueError:
        print("  ✅ get_module_class('unknown') raises ValueError")

    return True


def main():
    print("=" * 60)
    print("HYDRA Browser - Validación de Implementación")
    print("=" * 60)

    all_ok = True

    all_ok &= test_imports()
    all_ok &= test_instantiation()
    all_ok &= test_error_parser()
    all_ok &= test_module_registry()

    print("\n" + "=" * 60)
    if all_ok:
        print("🎉 TODOS LOS TESTS PASARON - Implementación válida")
        print("=" * 60)
        return 0
    else:
        print("❌ ALGUNOS TESTS FALLARON")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())