"""
Health Monitoring — Sistema de monitoreo de salud para conectores.

Proporciona métricas unificadas, alertas y dashboards para ARGOS.
"""

import asyncio
import logging
import statistics
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from hydra.browser.connectors.base import BaseConnector, HealthStatus, ConnectorState
from hydra.browser.connectors.registry import ConnectorRegistry, get_connector_registry

logger = logging.getLogger(__name__)


class AlertLevel(str, Enum):
    """Niveles de alerta."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Alerta generada por el monitor."""
    connector_name: str
    level: AlertLevel
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metric: Optional[str] = None
    value: Optional[float] = None
    threshold: Optional[float] = None
    acknowledged: bool = False


@dataclass
class ConnectorMetrics:
    """Métricas agregadas de un conector."""
    connector_name: str
    state: ConnectorState
    uptime_seconds: float
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float
    avg_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    last_execution: Optional[datetime]
    last_error: Optional[str]
    error_rate: float
    health_status: Optional[HealthStatus]
    capabilities_used: Dict[str, int] = field(default_factory=dict)
    alerts_active: int = 0


@dataclass
class SystemHealth:
    """Salud global del sistema de conectores."""
    timestamp: datetime
    total_connectors: int
    healthy_connectors: int
    degraded_connectors: int
    down_connectors: int
    total_executions: int
    global_success_rate: float
    avg_response_time_ms: float
    active_alerts: int
    connectors: Dict[str, ConnectorMetrics]


class HealthMonitor:
    """
    Monitor de salud centralizado para todos los conectores.
    
    Funciones:
    - Health checks periódicos
    - Recolección de métricas
    - Detección de anomalías
    - Alertas configurables
    - Historial de métricas (ventana deslizante)
    - Export para Prometheus/ARGOS
    """
    
    def __init__(
        self,
        registry: Optional[ConnectorRegistry] = None,
        check_interval_seconds: int = 30,
        metrics_window_seconds: int = 3600,  # 1 hora
        alert_thresholds: Optional[Dict[str, Any]] = None,
    ):
        self.registry = registry or get_connector_registry()
        self.check_interval = check_interval_seconds
        self.metrics_window = timedelta(seconds=metrics_window_seconds)
        self.alert_thresholds = alert_thresholds or self._default_thresholds()
        
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._metrics_history: Dict[str, deque] = {}  # connector_name -> deque of (timestamp, metrics)
        self._response_times: Dict[str, deque] = {}  # connector_name -> deque of response times
        self._alerts: List[Alert] = []
        self._alert_handlers: List[Callable[[Alert], Any]] = []
        self._lock = asyncio.Lock()
    
    def _default_thresholds(self) -> Dict[str, Any]:
        return {
            "health_check_failure": {"level": AlertLevel.CRITICAL, "consecutive": 3},
            "error_rate_high": {"level": AlertLevel.WARNING, "threshold": 0.1},  # 10%
            "error_rate_critical": {"level": AlertLevel.CRITICAL, "threshold": 0.5},  # 50%
            "response_time_high": {"level": AlertLevel.WARNING, "threshold_ms": 30000},
            "response_time_critical": {"level": AlertLevel.CRITICAL, "threshold_ms": 60000},
            "execution_timeout": {"level": AlertLevel.WARNING, "threshold_seconds": 300},
            "no_activity": {"level": AlertLevel.INFO, "threshold_seconds": 3600},
        }
    
    # ===== Control =====
    
    async def start(self) -> None:
        """Inicia el monitor."""
        if self._running:
            return
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("HealthMonitor iniciado")
    
    async def stop(self) -> None:
        """Detiene el monitor."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("HealthMonitor detenido")
    
    async def _monitor_loop(self) -> None:
        """Loop principal de monitoreo."""
        while self._running:
            try:
                await self._collect_metrics()
                await self._check_alerts()
            except Exception as e:
                logger.error(f"Error en monitor loop: {e}")
            
            await asyncio.sleep(self.check_interval)
    
    async def _collect_metrics(self) -> None:
        """Recolecta métricas de todos los conectores."""
        for name, instance in self.registry.get_all_instances().items():
            try:
                metrics = await self._collect_connector_metrics(name, instance)
                await self._store_metrics(name, metrics)
            except Exception as e:
                logger.error(f"Error recolectando métricas de {name}: {e}")
    
    async def _collect_connector_metrics(self, name: str, instance: BaseConnector) -> "ConnectorMetrics":
        """Recolecta métricas de un conector específico."""
        stats = instance.get_stats()
        health = await instance.health_check()
        
        # Calcular percentiles de tiempo de respuesta
        response_times = self._response_times.get(name, deque())
        if response_times:
            sorted_times = sorted(response_times)
            avg_rt = statistics.mean(sorted_times)
            p95_rt = sorted_times[int(len(sorted_times) * 0.95)] if len(sorted_times) > 1 else sorted_times[0]
            p99_rt = sorted_times[int(len(sorted_times) * 0.99)] if len(sorted_times) > 1 else sorted_times[0]
        else:
            avg_rt = p95_rt = p99_rt = 0.0
        
        return ConnectorMetrics(
            connector_name=name,
            state=instance.state,
            uptime_seconds=stats.get("uptime_seconds", 0),
            total_executions=stats.get("execution_count", 0),
            successful_executions=stats.get("execution_count", 0) - stats.get("error_count", 0),
            failed_executions=stats.get("error_count", 0),
            success_rate=1.0 - stats.get("error_rate", 0),
            avg_response_time_ms=avg_rt,
            p95_response_time_ms=p95_rt,
            p99_response_time_ms=p99_rt,
            last_execution=instance._last_activity if hasattr(instance, '_last_activity') else None,
            last_error=stats.get("last_health_check", {}).get("last_error"),
            error_rate=stats.get("error_rate", 0),
            health_status=instance._last_health_check,
            capabilities_used={},  # TODO: track per-capability usage
            alerts_active=sum(1 for a in self._alerts if a.connector_name == name and not a.acknowledged),
        )
    
    async def _store_metrics(self, name: str, metrics: ConnectorMetrics) -> None:
        """Almacena métricas en historial."""
        async with self._lock:
            if name not in self._metrics_history:
                self._metrics_history[name] = deque(maxlen=1000)
            self._metrics_history[name].append((datetime.utcnow(), metrics))
            
            # Mantener ventana de tiempo
            cutoff = datetime.utcnow() - self.metrics_window
            while self._metrics_history[name] and self._metrics_history[name][0][0] < cutoff:
                self._metrics_history[name].popleft()
            
            # Actualizar tiempos de respuesta para percentiles
            if name not in self._response_times:
                self._response_times[name] = deque(maxlen=1000)
            # El response time se actualiza via record_execution
    
    def record_execution(
        self,
        connector_name: str,
        capability: str,
        duration_ms: float,
        success: bool,
    ) -> None:
        """Registra una ejecución para métricas de tiempo de respuesta."""
        async def _record():
            async with self._lock:
                if connector_name not in self._response_times:
                    self._response_times[connector_name] = deque(maxlen=1000)
                self._response_times[connector_name].append(duration_ms)
        
        asyncio.create_task(_record())
    
    # ===== Alertas =====
    
    def add_alert_handler(self, handler: Callable[[Alert], Any]) -> None:
        """Registra handler para alertas (ej. Slack, Telegram, email)."""
        self._alert_handlers.append(handler)
    
    async def _check_alerts(self) -> None:
        """Evalúa thresholds y genera alertas."""
        for name, instance in self.registry.get_all_instances().items():
            stats = instance.get_stats()
            health = instance._last_health_check
            
            # Health check failures consecutivos
            if health and not health.healthy:
                # TODO: track consecutive failures
                pass
            
            # Error rate
            error_rate = stats.get("error_rate", 0)
            if error_rate >= self.alert_thresholds["error_rate_critical"]["threshold"]:
                await self._emit_alert(Alert(
                    connector_name=name,
                    level=AlertLevel.CRITICAL,
                    message=f"Error rate crítico: {error_rate:.1%}",
                    metric="error_rate",
                    value=error_rate,
                    threshold=self.alert_thresholds["error_rate_critical"]["threshold"],
                ))
            elif error_rate >= self.alert_thresholds["error_rate_high"]["threshold"]:
                await self._emit_alert(Alert(
                    connector_name=name,
                    level=AlertLevel.WARNING,
                    message=f"Error rate alto: {error_rate:.1%}",
                    metric="error_rate",
                    value=error_rate,
                    threshold=self.alert_thresholds["error_rate_high"]["threshold"],
                ))
            
            # Response time
            if health:
                rt = health.response_time_ms
                if rt >= self.alert_thresholds["response_time_critical"]["threshold_ms"]:
                    await self._emit_alert(Alert(
                        connector_name=name,
                        level=AlertLevel.CRITICAL,
                        message=f"Response time crítico: {rt:.0f}ms",
                        metric="response_time_ms",
                        value=rt,
                        threshold=self.alert_thresholds["response_time_critical"]["threshold_ms"],
                    ))
                elif rt >= self.alert_thresholds["response_time_high"]["threshold_ms"]:
                    await self._emit_alert(Alert(
                        connector_name=name,
                        level=AlertLevel.WARNING,
                        message=f"Response time alto: {rt:.0f}ms",
                        metric="response_time_ms",
                        value=rt,
                        threshold=self.alert_thresholds["response_time_high"]["threshold_ms"],
                    ))
            
            # No activity
            if hasattr(instance, '_last_activity'):
                inactive_seconds = (datetime.utcnow() - instance._last_activity).total_seconds()
                if inactive_seconds >= self.alert_thresholds["no_activity"]["threshold_seconds"]:
                    await self._emit_alert(Alert(
                        connector_name=name,
                        level=AlertLevel.INFO,
                        message=f"Sin actividad por {inactive_seconds/3600:.1f}h",
                        metric="inactive_seconds",
                        value=inactive_seconds,
                        threshold=self.alert_thresholds["no_activity"]["threshold_seconds"],
                    ))
    
    async def _emit_alert(self, alert: Alert) -> None:
        """Emite alerta a handlers registrados."""
        # Evitar duplicados recientes
        recent = [a for a in self._alerts 
                  if a.connector_name == alert.connector_name 
                  and a.metric == alert.metric
                  and (datetime.utcnow() - a.timestamp).total_seconds() < 300]
        if recent:
            return
        
        self._alerts.append(alert)
        logger.warning(f"ALERT [{alert.level.value}] {alert.connector_name}: {alert.message}")
        
        for handler in self._alert_handlers:
            try:
                await handler(alert)
            except Exception as e:
                logger.error(f"Error en alert handler: {e}")
    
    # ===== API Pública =====
    
    def get_system_health(self) -> SystemHealth:
        """Obtiene salud global del sistema."""
        connectors = {}
        total_exec = 0
        total_success = 0
        
        for name, instance in self.registry.get_all_instances().items():
            # Usar métricas más recientes del historial
            history = self._metrics_history.get(name, deque())
            latest = history[-1][1] if history else None
            
            if latest:
                connectors[name] = latest
                total_exec += latest.total_executions
                total_success += latest.successful_executions
            else:
                stats = instance.get_stats()
                connectors[name] = ConnectorMetrics(
                    connector_name=name,
                    state=instance.state,
                    uptime_seconds=stats.get("uptime_seconds", 0),
                    total_executions=stats.get("execution_count", 0),
                    successful_executions=stats.get("execution_count", 0) - stats.get("error_count", 0),
                    failed_executions=stats.get("error_count", 0),
                    success_rate=1.0 - stats.get("error_rate", 0),
                    avg_response_time_ms=0,
                    p95_response_time_ms=0,
                    p99_response_time_ms=0,
                    last_execution=None,
                    last_error=None,
                    error_rate=stats.get("error_rate", 0),
                    health_status=instance._last_health_check,
                )
                total_exec += stats.get("execution_count", 0)
                total_success += stats.get("execution_count", 0) - stats.get("error_count", 0)
        
        healthy = sum(1 for c in connectors.values() if c.health_status and c.health_status.healthy)
        degraded = sum(1 for c in connectors.values() if c.health_status and not c.health_status.healthy and c.state != ConnectorState.ERROR)
        down = sum(1 for c in connectors.values() if c.state == ConnectorState.ERROR)
        
        return SystemHealth(
            timestamp=datetime.utcnow(),
            total_connectors=len(connectors),
            healthy_connectors=healthy,
            degraded_connectors=degraded,
            down_connectors=down,
            total_executions=total_exec,
            global_success_rate=total_success / max(total_exec, 1),
            avg_response_time_ms=statistics.mean([c.avg_response_time_ms for c in connectors.values()]) if connectors else 0,
            active_alerts=sum(1 for a in self._alerts if not a.acknowledged),
            connectors=connectors,
        )
    
    def get_connector_metrics(self, name: str) -> Optional[ConnectorMetrics]:
        """Obtiene métricas más recientes de un conector."""
        history = self._metrics_history.get(name, deque())
        return history[-1][1] if history else None
    
    def get_metrics_history(self, name: str, since: Optional[datetime] = None) -> List[ConnectorMetrics]:
        """Obtiene historial de métricas."""
        history = self._metrics_history.get(name, deque())
        if since:
            return [m for t, m in history if t >= since]
        return [m for t, m in history]
    
    def get_alerts(
        self,
        connector_name: Optional[str] = None,
        level: Optional[AlertLevel] = None,
        acknowledged: Optional[bool] = None,
        limit: int = 100,
    ) -> List[Alert]:
        """Obtiene alertas con filtros."""
        alerts = self._alerts
        if connector_name:
            alerts = [a for a in alerts if a.connector_name == connector_name]
        if level:
            alerts = [a for a in alerts if a.level == level]
        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]
        return alerts[-limit:]
    
    def acknowledge_alert(self, alert_index: int) -> bool:
        """Marca alerta como reconocida."""
        if 0 <= alert_index < len(self._alerts):
            self._alerts[alert_index].acknowledged = True
            return True
        return False
    
    def get_prometheus_metrics(self) -> str:
        """Exporta métricas en formato Prometheus."""
        lines = [
            "# HELP hydra_connector_state Estado del conector (0=down, 1=degraded, 2=healthy)",
            "# TYPE hydra_connector_state gauge",
            "# HELP hydra_connector_executions_total Total de ejecuciones",
            "# TYPE hydra_connector_executions_total counter",
            "# HELP hydra_connector_success_rate Tasa de éxito",
            "# TYPE hydra_connector_success_rate gauge",
            "# HELP hydra_connector_response_time_ms Tiempo de respuesta promedio",
            "# TYPE hydra_connector_response_time_ms gauge",
            "# HELP hydra_connector_error_rate Tasa de error",
            "# TYPE hydra_connector_error_rate gauge",
            "# HELP hydra_alerts_active Alertas activas",
            "# TYPE hydra_alerts_active gauge",
        ]
        
        health = self.get_system_health()
        for name, metrics in health.connectors.items():
            state_val = 2 if metrics.health_status and metrics.health_status.healthy else (1 if metrics.state != ConnectorState.ERROR else 0)
            lines.append(f'hydra_connector_state{{connector="{name}"}} {state_val}')
            lines.append(f'hydra_connector_executions_total{{connector="{name}"}} {metrics.total_executions}')
            lines.append(f'hydra_connector_success_rate{{connector="{name}"}} {metrics.success_rate}')
            lines.append(f'hydra_connector_response_time_ms{{connector="{name}"}} {metrics.avg_response_time_ms}')
            lines.append(f'hydra_connector_error_rate{{connector="{name}"}} {metrics.error_rate}')
        
        lines.append(f'hydra_alerts_active {health.active_alerts}')
        
        return "\n".join(lines)


# ===== Handlers de Alerta Predefinidos =====

async def log_alert_handler(alert: Alert) -> None:
    """Handler que loguea alertas."""
    logger.log(
        logging.WARNING if alert.level == AlertLevel.WARNING else logging.ERROR,
        f"ALERT [{alert.level.value}] {alert.connector_name}: {alert.message}"
    )


async def slack_alert_handler(webhook_url: str) -> Callable[[Alert], Any]:
    """Factory para handler de Slack."""
    import aiohttp
    
    async def handler(alert: Alert) -> None:
        color = {
            AlertLevel.INFO: "#36a64f",
            AlertLevel.WARNING: "#ff9800",
            AlertLevel.CRITICAL: "#f44336",
        }.get(alert.level, "#808080")
        
        payload = {
            "attachments": [{
                "color": color,
                "title": f"HYDRA Alert: {alert.connector_name}",
                "text": alert.message,
                "fields": [
                    {"title": "Level", "value": alert.level.value, "short": True},
                    {"title": "Metric", "value": alert.metric or "N/A", "short": True},
                    {"title": "Value", "value": str(alert.value) if alert.value else "N/A", "short": True},
                    {"title": "Threshold", "value": str(alert.threshold) if alert.threshold else "N/A", "short": True},
                ],
                "ts": int(alert.timestamp.timestamp()),
            }]
        }
        async with aiohttp.ClientSession() as session:
            await session.post(webhook_url, json=payload)
    
    return handler


# ===== Instancia Global =====

_global_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """Obtiene monitor global (singleton)."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = HealthMonitor()
    return _global_monitor