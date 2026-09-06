"""
Connector Registry — Registro automático de conectores.

Permite que los conectores se registren automáticamente sin modificar
el núcleo de BrowserManager. Basado en entry points o descubrimiento de módulos.
"""

import importlib
import logging
import pkgutil
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type

from hydra.browser.connectors.base import BaseConnector, ConnectorConfig, ConnectorState
from hydra.browser.connectors.capabilities import ConnectorCapabilities

logger = logging.getLogger(__name__)


@dataclass
class ConnectorRegistration:
    """Registro de un conector en el registry."""
    name: str
    connector_class: Type
    capabilities: "ConnectorCapabilities"
    version: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


class ConnectorRegistry:
    """
    Registro central de conectores disponibles.
    
    Características:
    - Auto-descubrimiento via entry points o paquetes
    - Registro manual de conectores
    - Filtrado por capacidades
    - Validación de dependencias
    - Instanciación lazy
    """
    
    def __init__(self):
        self._connectors: Dict[str, ConnectorRegistration] = {}
        self._instances: Dict[str, Any] = {}
        self._discovered = False
    
    def register(
        self,
        name: str,
        connector_class: Type,
        capabilities: "ConnectorCapabilities",
        version: str = "1.0.0",
        description: str = "",
        dependencies: List[str] = None,
        config_schema: Dict[str, Any] = None,
        enabled: bool = True,
    ) -> None:
        """Registra un conector manualmente."""
        if name in self._connectors:
            logger.warning(f"Conector '{name}' ya registrado, sobrescribiendo")
        
        registration = ConnectorRegistration(
            name=name,
            connector_class=connector_class,
            capabilities=capabilities,
            version=version,
            description=description,
            dependencies=dependencies or [],
            config_schema=config_schema or {},
            enabled=enabled,
        )
        self._connectors[name] = registration
        logger.info(f"Conector registrado: {name} v{version} ({len(capabilities.supported)} capacidades)")
    
    def unregister(self, name: str) -> bool:
        """Elimina un conector del registro."""
        if name in self._connectors:
            del self._connectors[name]
            self._instances.pop(name, None)
            logger.info(f"Conector desregistrado: {name}")
            return True
        return False
    
    def get(self, name: str) -> Optional[ConnectorRegistration]:
        """Obtiene registro de un conector."""
        return self._connectors.get(name)
    
    def get_class(self, name: str) -> Optional[Type]:
        """Obtiene la clase del conector."""
        reg = self._connectors.get(name)
        return reg.connector_class if reg else None
    
    def get_capabilities(self, name: str) -> Optional["ConnectorCapabilities"]:
        """Obtiene capacidades de un conector."""
        reg = self._connectors.get(name)
        return reg.capabilities if reg else None
    
    def list_all(self) -> List[Dict[str, Any]]:
        """Lista todos los conectores registrados."""
        return [
            {
                "name": reg.name,
                "version": reg.version,
                "description": reg.description,
                "enabled": reg.enabled,
                "capabilities_count": len(reg.capabilities.supported),
                "capabilities": [c.value for c in reg.capabilities.supported],
                "dependencies": reg.dependencies,
            }
            for reg in self._connectors.values()
            if reg.enabled
        ]
    
    def find_by_capability(self, capability: str) -> List[str]:
        """Busca conectores que soporten una capacidad."""
        matching = []
        for name, reg in self._connectors.items():
            if reg.enabled and capability in [c.value for c in reg.capabilities.supported]:
                matching.append(name)
        return matching
    
    def create_instance(
        self,
        name: str,
        config: "ConnectorConfig",
    ) -> Optional[Any]:
        """Crea instancia de un conector (lazy instantiation)."""
        reg = self._connectors.get(name)
        if not reg:
            logger.error(f"Conector no registrado: {name}")
            return None
        
        if not reg.enabled:
            logger.warning(f"Conector deshabilitado: {name}")
            return None
        
        if name in self._instances:
            logger.warning(f"Instancia ya existe para {name}, retornando existente")
            return self._instances[name]
        
        try:
            # Verificar dependencias
            for dep in reg.dependencies:
                if dep not in self._connectors:
                    logger.error(f"Dependencia faltante para {name}: {dep}")
                    return None
            
            instance = reg.connector_class.__new__(reg.connector_class)
            # El __init__ se llama manualmente para pasar config
            instance.__init__(config)
            self._instances[name] = instance
            logger.info(f"Instancia creada para conector: {name}")
            return instance
            
        except Exception as e:
            logger.error(f"Error creando instancia de {name}: {e}")
            return None
    
    def get_instance(self, name: str) -> Optional[Any]:
        """Obtiene instancia existente."""
        return self._instances.get(name)
    
    async def initialize_all(self, browser_manager) -> Dict[str, bool]:
        """Inicializa todos los conectores habilitados."""
        results = {}
        for name, reg in self._connectors.items():
            if not reg.enabled:
                continue
            if name in self._instances:
                continue
            
            # Crear config básica
            config = ConnectorConfig(service_name=name)
            instance = self.create_instance(name, ConnectorConfig(service_name=name))
            if instance:
                success = await instance.connect(browser_manager)
                results[name] = success
            else:
                results[name] = False
        return results
    
    async def health_check_all(self) -> Dict[str, Any]:
        """Health check de todas las instancias activas."""
        results = {}
        for name, instance in self._instances.items():
            try:
                health = await instance.health_check()
                results[name] = {
                    "healthy": health.healthy,
                    "state": health.state.value if hasattr(health.state, 'value') else str(health.state),
                    "response_time_ms": health.response_time_ms,
                    "last_error": health.last_error,
                }
            except Exception as e:
                results[name] = {
                    "healthy": False,
                    "error": str(e),
                }
        return results
    
    async def close_all(self) -> Dict[str, bool]:
        """Cierra todas las instancias activas."""
        results = {}
        for name, instance in list(self._instances.items()):
            try:
                success = await instance.close()
                results[name] = success
                del self._instances[name]
            except Exception as e:
                logger.error(f"Error cerrando {name}: {e}")
                results[name] = False
        return results
    
    def get_instance(self, name: str) -> Optional[Any]:
        return self._instances.get(name)
    
    def get_all_instances(self) -> Dict[str, Any]:
        return dict(self._instances)
    
    # ===== Auto-discovery =====
    
    def discover(self, package_prefix: str = "hydra") -> int:
        """
        Descubre conectores automáticamente buscando módulos
        con atributo `CONNECTOR_CLASS` o `register_connector()`.
        """
        if self._discovered:
            return 0
        
        count = 0
        try:
            # Buscar en src/hydra/*/
            for finder, name, ispkg in pkgutil.iter_modules(
                ["/home/genesis/opt/genesis/HYDRA/src/hydra"],
                prefix="hydra."
            ):
                if not ispkg:
                    continue
                
                # Verificar si el paquete tiene conector
                if name.startswith("hydra.") and name != "hydra.browser":
                    try:
                        module = importlib.import_module(name)
                        if hasattr(module, "CONNECTOR_CLASS"):
                            cls = module.CONNECTOR_CLASS
                            caps = getattr(module, "CONNECTOR_CAPABILITIES", None)
                            if caps:
                                self.register(
                                    name=name.split(".")[-1],
                                    connector_class=cls,
                                    capabilities=caps,
                                    version=getattr(module, "__version__", "1.0.0"),
                                    description=getattr(module, "__doc__", ""),
                                )
                                count += 1
                        elif hasattr(module, "register_connector"):
                            module.register_connector(self)
                            count += 1
                    except Exception as e:
                        logger.debug(f"No se pudo cargar conector de {name}: {e}")
            
            self._discovered = True
            logger.info(f"Auto-discovery completado: {count} conectores encontrados")
            
        except Exception as e:
            logger.warning(f"Auto-discovery falló: {e}")
        
        return count
    
    def clear(self) -> None:
        """Limpia el registro completamente."""
        self._connectors.clear()
        self._instances.clear()
        self._discovered = False


# ===== Registry Global (Singleton) =====

_global_registry: Optional["ConnectorRegistry"] = None


def get_connector_registry() -> "ConnectorRegistry":
    """Obtiene el registry global (singleton)."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ConnectorRegistry()
    return _global_registry


def register_connector(
    name: str,
    connector_class: Type,
    capabilities: "ConnectorCapabilities",
    **kwargs,
) -> None:
    """Helper para registrar conector en registry global."""
    get_connector_registry().register(name, connector_class, capabilities, **kwargs)


def get_connector(name: str) -> Optional[Type]:
    """Obtiene clase de conector del registry global."""
    return get_connector_registry().get_class(name)


# ===== Decorador para registro automático =====

def connector(
    name: str,
    capabilities: "ConnectorCapabilities",
    version: str = "1.0.0",
    description: str = "",
    dependencies: List[str] = None,
    config_schema: Dict[str, Any] = None,
    enabled: bool = True,
):
    """
    Decorador para registrar conector automáticamente.
    
    Uso:
        @connector("miservicio", capabilities=MY_CAPABILITIES)
        class MiServicioConnector(BaseConnector):
            ...
    """
    def decorator(cls):
        get_connector_registry().register(
            name=name,
            connector_class=cls,
            capabilities=capabilities,
            version=version,
            description=description or cls.__doc__ or "",
        )
        return cls
    return decorator