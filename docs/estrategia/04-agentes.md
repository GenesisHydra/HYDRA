# Arquitectura de Agentes IA Internos

## 1. Visión General
Este documento describe la arquitectura propuesta para los **agentes IA internos** de Argos, definiendo sus **roles**, **mecanismos de comunicación**, **ciclo de vida** y **supervisión**. La arquitectura se alinea con los principios de modularidad, escalabilidad y resiliencia presentes en el resto del ecosistema (ver `docs/architecture/*.md`).

---

## 2. Roles de los Agentes
| Rol | Responsabilidad principal | Sub‑componentes clave |
|---|---|---|
| **Coordinador (Director General)** | Orquesta el flujo de trabajo, asigna tareas a agentes ejecutores, gestiona prioridades y adapta la estrategia a cambios del entorno. | `manager/domain/agent/service.py`, `planner/strategy.py` |
| **Ejecutor (Operador)** | Implementa acciones concretas (código, llamadas a proveedores, interacción con subsistemas). | `executor/base.py`, `runtime/heartbeat.py` |
| **Gestor de Conocimiento (Knowledge Manager)** | Accede, actualiza y publica datos en la memoria cognitiva/semántica; provee contexto a otros agentes. | `memory/cognitive/semantic_memory.py`, `knowledge/consultation.py` |
| **Supervisor (Watchdog)** | Monitorea salud, métricas y cumplimiento de SLA; detecta fallos y dispara auto‑recuperación o escalado. | `runtime/watchdog.py`, `supervision/service.py` |
| **Interfaz (Gateway/Adapter)** | Expone APIs externas (REST, CLI, voz) y traduce eventos externos al bus interno. | `gateway/gateway.py`, `users_api/api.py` |

> Cada agente está modelado como una **entidad de dominio** (`src/argos/manager/domain/agent`) con registro en el `AgentRegistry` y persiste su estado en la base SQLite (`infra/sqlite_store.py`).

---

## 3. Comunicación entre Agentes
1. **Message Bus (Event‑Driven)** – Implementado con el `EventBus` (`src/argos/events/bus.py`). Todos los agentes publican y suscriben a eventos tipificados (`AgentCreated`, `TaskCompleted`, `HealthCheck`).
2. **RPC Síncrono** – Cuando un agente necesita una respuesta inmediata (p. ej., consulta de conocimiento), usa el patrón **Command‑Query** a través de interfaces Python (`service` classes) que retornan `Result` objects.
3. **Cola de Tareas** – El `TaskQueue` (`src/argos/planner/planner.py`) gestiona prioridades y permite *back‑pressure* para evitar sobrecarga de los ejecutores.
4. **Persistencia de Mensajes** – Cada evento importante se registra en la tabla `event_log` de la memoria cognitiva para auditoría y replay.

---

## 4. Ciclo de Vida del Agente
```
Provision → Init → Ready → Operate → Scale/Update → Decommission
```
| Etapa | Acción | Herramientas |
|---|---|---|
| **Provision** | Creación de registro en `AgentRegistry`; asignación de UUID y configuración base. | `manager/domain/agent/repository.py` |
| **Init** | Carga de dependencias, conexión a bus, verificación de salud inicial. | `runtime/bootstrap.py` |
| **Ready** | Estado “idle”; agente anuncia disponibilidad vía `AgentReady` event. | `event_bus.publish()` |
| **Operate** | Procesamiento de tareas; ciclo de heartbeat (`runtime/heartbeat.py`). | `heartbeat_registry` |
| **Scale/Update** | Hot‑swap de lógica vía hot‑reload de plugins; aumento de réplicas en `Supervisor`. | `runtime/provider_policy.py` |
| **Decommission** | Desregistro, flush de cola, archivado de logs. | `agent_registry.remove()` |

---

## 5. Mecanismos de Supervisión
1. **Watchdog Central** – Un agente supervisor (`SupervisorAgent`) ejecuta un bucle de health‑checks cada 5 s contra todos los agentes registrados.
2. **Métricas** – Cada agente expone métricas vía `prometheus_client` (latencia, error_rate, queue_depth). Los datos se agregan en `monitoring/`.
3. **Alertas y Escalado** – Si la métrica supera umbrales, el watchdog dispara:
   - **Auto‑recuperación** (reinicio del agente).
   - **Escalado Horizontal** (instancia adicional vía `runtime/sustain.py`).
   - **Escalada a Operaciones** (push a Slack/Telegram usando `tools/notification.py`).
4. **Auditoría** – Todos los eventos críticos se guardan en `event_log` y se exportan a `docs/hydra/auditorias/` como auditorías estructuradas.

---

## 6. Diagrama de Arquitectura (texto)
```
[Gateway] <---> [Message Bus] <---> [Coordinador]
         \            |            /
          \           |           /
           \          v          /
            --> [Ejecutores] <--
           /          |          \
          /           v           \
 [Gestor de Conocimiento]   [Supervisor]
```
*El diagrama simplificado muestra los flujos de mensajes y dependencias críticas.*

---

## 7. Conformidad y Buenas Prácticas
- **Inmutabilidad de Config** – Las configuraciones de agentes se almacenan en `src/argos/config.py` y son cargadas una sola vez.
- **Idempotencia** – Operaciones de provisionamiento y desactivación son idempotentes.
- **Observabilidad** – Logs estructurados (`json`) y trazas distribuidas usando OpenTelemetry (ya presente en `src/argos/observability`).
- **Seguridad** – Cada agente usa tokens de servicio (`runtime/provider_policy.py`) y verifica permisos antes de ejecutar acciones críticas.

---

*Este documento debe mantenerse actualizado en el repositorio bajo `HYDRA/docs/estrategia/04-agentes.md` y versionarse mediante los procesos habituales de revisión de documentos.*
