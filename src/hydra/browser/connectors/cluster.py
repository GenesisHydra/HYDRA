"""
Cluster Interfaces — Interfaces preparadas para Browser Cluster distribuido.

Diseñadas para migración futura a múltiples workers en varios VPS
sin romper compatibilidad con conectores existentes.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

logger = logging.getLogger(__name__)


class NodeRole(str, Enum):
    """Roles de nodo en el cluster."""
    COORDINATOR = "coordinator"      # Nodo coordinador (uno solo)
    WORKER = "worker"                # Workers que ejecutan tareas
    STANDBY = "standby"              # Workers en reserva


class NodeStatus(str, Enum):
    """Estados de nodo."""
    STARTING = "starting"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    SHUTTING_DOWN = "shutting_down"
    OFFLINE = "offline"


@dataclass
class NodeInfo:
    """Información de un nodo del cluster."""
    node_id: str
    role: NodeRole
    status: NodeStatus
    host: str
    port: int
    capabilities: Set[str] = field(default_factory=set)  # Capacidades que puede ejecutar
    max_concurrent_tasks: int = 10
    current_tasks: int = 0
    started_at: datetime = field(default_factory=datetime.utcnow)
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def endpoint(self) -> str:
        return f"{self.host}:{self.port}"
    
    @property
    def available_capacity(self) -> int:
        return max(0, self.max_concurrent_tasks - self.current_tasks)
    
    @property
    def is_available(self) -> bool:
        return self.status == NodeStatus.HEALTHY and self.available_capacity > 0


@dataclass
class TaskRequest:
    """Solicitud de ejecución de tarea."""
    task_id: str = field(default_factory=lambda: str(uuid4()))
    capability: str
    params: Dict[str, Any]
    connector_name: str
    priority: int = 5  # 1=highest, 10=lowest
    timeout_seconds: int = 300
    required_capabilities: List[str] = field(default_factory=list)
    affinity: Optional[str] = None  # node_id preferido
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    """Resultado de ejecución de tarea."""
    task_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    duration_ms: float = 0
    executed_on: Optional[str] = None  # node_id
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime = field(default_factory=datetime.utcnow)
    artifacts: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)


# ===== Interfaces Cluster =====

class IClusterCoordinator(ABC):
    """Interfaz del coordinador de cluster (single-writer)."""
    
    @abstractmethod
    async def register_node(self, node: NodeInfo) -> bool:
        """Registra un worker en el cluster."""
        pass
    
    @abstractmethod
    async def unregister_node(self, node_id: str) -> bool:
        """Desregistra un worker."""
        pass
    
    @abstractmethod
    async def submit_task(self, task: TaskRequest) -> str:
        """Envía tarea al cluster, retorna task_id."""
        pass
    
    @abstractmethod
    async def get_task_result(self, task_id: str, timeout: float = 300) -> TaskResult:
        """Obtiene resultado de tarea (blocking)."""
        pass
    
    @abstractmethod
    async def cancel_task(self, task_id: str) -> bool:
        """Cancela tarea pendiente."""
        pass
    
    @abstractmethod
    async def get_cluster_status(self) -> Dict[str, Any]:
        """Estado global del cluster."""
        pass
    
    @abstractmethod
    async def get_node_status(self, node_id: str) -> Optional[NodeInfo]:
        """Estado de un nodo específico."""
        pass


class IClusterWorker(ABC):
    """Interfaz del worker de cluster (ejecuta tareas)."""
    
    @abstractmethod
    async def start(self, coordinator_endpoint: str) -> bool:
        """Inicia worker y se registra en coordinador."""
        pass
    
    @abstractmethod
    async def stop(self) -> bool:
        """Detiene worker gracefully."""
        pass
    
    @abstractmethod
    async def execute_task(self, task: TaskRequest) -> TaskResult:
        """Ejecuta una tarea asignada."""
        pass
    
    @abstractmethod
    async def get_capabilities(self) -> Set[str]:
        """Capacidades que este worker puede ejecutar."""
        pass
    
    @abstractmethod
    async def health_check(self) -> NodeStatus:
        """Health check del worker."""
        pass


class ITaskQueue(ABC):
    """Interfaz de cola de tareas distribuida."""
    
    @abstractmethod
    async def enqueue(self, task: TaskRequest) -> bool:
        pass
    
    @abstractmethod
    async def dequeue(self, worker_capabilities: Set[str], max_tasks: int = 1) -> List[TaskRequest]:
        pass
    
    @abstractmethod
    async def requeue(self, task: TaskRequest) -> bool:
        pass
    
    @abstractmethod
    async def get_pending_count(self, capability: Optional[str] = None) -> int:
        pass


# ===== Implementación Local (Single-Node) =====

class LocalClusterCoordinator(IClusterCoordinator):
    """
    Coordinador local para modo single-node (actual).
    Compatible con interfaz de cluster para migración futura.
    """
    
    def __init__(self, browser_manager):
        self.browser_manager = browser_manager
        self._nodes: Dict[str, NodeInfo] = {}
        self._task_queue: asyncio.Queue = asyncio.Queue()
        self._results: Dict[str, asyncio.Future] = {}
        self._running = False
        self._dispatcher_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._dispatcher_task = asyncio.create_task(self._dispatch_loop())
        logger.info("LocalClusterCoordinator iniciado (modo single-node)")
    
    async def stop(self) -> None:
        self._running = False
        if self._dispatcher_task:
            self._dispatcher_task.cancel()
            try:
                await self._dispatcher_task
            except asyncio.CancelledError:
                pass
        logger.info("LocalClusterCoordinator detenido")
    
    async def register_node(self, node: NodeInfo) -> bool:
        if node.node_id in self._nodes:
            return False
        self._nodes[node.node_id] = node
        logger.info(f"Nodo registrado (local): {node.node_id}")
        return True
    
    async def unregister_node(self, node_id: str) -> bool:
        if node_id in self._nodes:
            del self._nodes[node_id]
            logger.info(f"Nodo desregistrado: {node_id}")
            return True
        return False
    
    async def submit_task(self, task: TaskRequest) -> str:
        await self._task_queue.put(task)
        # Crear future para resultado
        future = asyncio.Future()
        self._results[task.task_id] = future
        return task.task_id
    
    async def get_task_result(self, task_id: str, timeout: float = 300) -> TaskResult:
        future = self._results.get(task_id)
        if not future:
            raise ValueError(f"Task no encontrado: {task_id}")
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Task {task_id} timeout después de {timeout}s")
    
    async def cancel_task(self, task_id: str) -> bool:
        # En modo local, no se puede cancelar fácilmente
        return False
    
    async def get_cluster_status(self) -> Dict[str, Any]:
        return {
            "mode": "local",
            "nodes": len(self._nodes),
            "pending_tasks": self._task_queue.qsize(),
            "active_tasks": len(self._results),
            "nodes_detail": {nid: n.__dict__ for nid, n in self._nodes.items()},
        }
    
    async def get_node_status(self, node_id: str) -> Optional[NodeInfo]:
        return self._nodes.get(node_id)
    
    async def _dispatch_loop(self) -> None:
        """Loop que despacha tareas al browser_manager local."""
        while self._running:
            try:
                task = await asyncio.wait_for(self._task_queue.get(), timeout=1.0)
                
                # Ejecutar via browser_manager
                result = await self._execute_local_task(task)
                
                # Resolver future
                future = self._results.pop(task.task_id, None)
                if future and not future.done():
                    future.set_result(result)
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error en dispatch loop: {e}")
                if 'task' in locals():
                    future = self._results.pop(task.task_id, None)
                    if future and not future.done():
                        future.set_exception(e)
    
    async def _execute_local_task(self, task: TaskRequest) -> TaskResult:
        """Ejecuta tarea usando browser_manager local."""
        start = datetime.utcnow()
        try:
            # Obtener conector del registry
            from hydra.browser.connectors.registry import get_connector_registry
            registry = get_connector_registry()
            instance = registry.get_instance(task.connector_name)
            
            if not instance:
                # Intentar crear e inicializar
                from hydra.browser.connectors.base import ConnectorConfig
                instance = registry.create_instance(
                    task.connector_name,
                    ConnectorConfig(service_name=task.connector_name)
                )
                if instance:
                    await instance.connect(self.browser_manager)
            
            if not instance:
                return TaskResult(
                    task_id=task.task_id,
                    success=False,
                    error=f"Conector no disponible: {task.connector_name}",
                    executed_on="local",
                )
            
            # Ejecutar capacidad
            from hydra.browser.connectors.capabilities import Capability
            capability = Capability(task.capability)
            exec_result = await instance.execute(capability, task.params)
            
            return TaskResult(
                task_id=task.task_id,
                success=exec_result.success,
                result=exec_result.result,
                error=exec_result.error,
                duration_ms=exec_result.duration_ms,
                executed_on="local",
                artifacts=exec_result.artifacts,
                metrics={"capability": task.capability},
            )
            
        except Exception as e:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                error=str(e),
                executed_on="local",
            )


# ===== Factory para Cluster Mode =====

class ClusterMode(str, Enum):
    LOCAL = "local"
    DISTRIBUTED = "distributed"


def create_cluster_coordinator(
    mode: ClusterMode,
    browser_manager,
    **kwargs,
) -> IClusterCoordinator:
    """Factory para crear coordinador según modo."""
    if mode == ClusterMode.LOCAL:
        return LocalClusterCoordinator(browser_manager)
    else:
        # TODO: Implementar coordinador distribuido (Redis, etcd, etc.)
        raise NotImplementedError(f"Modo cluster {mode.value} no implementado aún")


def create_cluster_worker(
    mode: ClusterMode,
    browser_manager,
    coordinator_endpoint: str,
    **kwargs,
) -> "IClusterWorker":
    """Factory para crear worker según modo."""
    if mode == ClusterMode.LOCAL:
        # En modo local, el worker es el propio browser_manager
        raise NotImplementedError("Worker local no necesario (coordinador ejecuta directamente)")
    else:
        raise NotImplementedError(f"Worker distribuido no implementado aún")


# ===== Configuración Cluster =====

@dataclass
class ClusterConfig:
    """Configuración del cluster."""
    mode: ClusterMode = ClusterMode.LOCAL
    coordinator_host: str = "localhost"
    coordinator_port: int = 8765
    worker_port_range: tuple = (8766, 8865)
    heartbeat_interval_seconds: int = 10
    task_timeout_seconds: int = 300
    max_retries: int = 3
    enable_metrics: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)