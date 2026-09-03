# MVP y Roadmap de HYDRA

## 1. Visión del MVP
El **MVP de HYDRA** es una plataforma de micro‑servicios que permite a usuarios (startups de IA, desarrolladores senior y empresas medianas) orquestar agentes IA internos de forma segura, escalable y observable.  Se entrega como un conjunto de APIs REST + CLI + web UI mínima que cubre los flujos esenciales de creación, ejecución y monitorización de agentes.

## 2. Funcionalidades críticas (prioridad alta)
| Prioridad | Funcionalidad | Descripción breve | Dependencias clave |
|-----------|----------------|-------------------|--------------------|
| **1** | **Core Agent Registry** | Registro, descubrimiento y gestión de ciclo de vida de agentes (provision, init, decommission). | `src/argos/manager/domain/agent`, SQLite store. |
| **2** | **Task Queue & Execution Engine** | Envío de tareas a agentes ejecutores, gestión de colas y retries. | `src/argos/planner/planner.py`, EventBus. |
| **3** | **Message Bus (Event‑Driven)** | Comunicación asincrónica entre agentes, auditoría de eventos. | `src/argos/events/bus.py`. |
| **4** | **API Gateway & CLI** | Exposición de endpoints REST y comando `hydra-cli` para crear/consultar agentes. | `gateway/gateway.py`, `users_api/api.py`. |
| **5** | **Observabilidad básica** | Métricas Prometheus, logs estructurados y trazas OpenTelemetry. | `src/argos/observability/`. |
| **6** | **Security & Auth** | Tokens de servicio, RBAC básico, integración con Vault (dev). | `runtime/provider_policy.py`. |

## 3. Roadmap (6 meses)
| Mes | Fase | Hitos principales | Salida esperada |
|-----|------|-------------------|-----------------|
| **1** | **Planificación & Setup** | • Crear repositorio HYDRA scaffold.<br>• Definir arquitectura de micro‑servicios (ver `04‑agentes.md`).<br>• Configurar CI básica (lint, unit tests). | Repo inicial, CI pipeline funcionando. |
| **2** | **Desarrollo Core** | • Implementar **Agent Registry** y persistencia.<br>• Implementar **Task Queue** y motor de ejecución.<br>• Exponer APIs mínimas (`/agents`, `/tasks`). | API funcional + pruebas unitarias (>80 % cobertura). |
| **3** | **Comunicación & Observabilidad** | • Integrar **Event Bus**.<br>• Añadir métricas Prometheus y logs JSON.<br>• Primer dashboard Grafana. | Sistema de eventos y monitorización operativa. |
| **4** | **Seguridad & CLI** | • Implementar autenticación JWT + RBAC.<br>• CLI `hydra` para gestión de agentes.<br>• Integración con Vault (dev). | Acceso seguro vía API/CLI, pruebas de seguridad. |
| **5** | **Pruebas de Integración & Validación** | • Pruebas end‑to‑end (crear agente → ejecutar tarea → obtener evento).<br>• Test de resiliencia (simular fallo de agente).<br>• Validación de métricas y logs. | Suite de integración aprobada, reporte de pruebas. |
| **6** | **Beta Release & Feedback Loop** | • Despliegue en entorno dev (EKS vía Helm).<br>• Programa piloto con 3 usuarios clave.<br>• Recopilación de feedback y ajustes rápidos. | MVP en beta, documentación básica (`07‑mvp‑roadmap.md`). |

## 4. Estrategia de pruebas y validación
1. **Unit Tests** – `pytest`, coverage ≥ 85 % para cada módulo.
2. **Integration Tests** – Docker Compose con servicios mock (Redis, Postgres) que ejecuten los flujos completos.
3. **Contract Tests** – Verificar que la API cumpla con OpenAPI spec (generado en `docs/`).
4. **Performance Tests** – Simular 100 concurrent tasks usando `locust` en la fase 5.
5. **Security Scans** – `bandit`, `trivy` y scans de dependencias en CI.
6. **User Acceptance** – Checklist de criterios de aceptación para cada función crítica, revisado por el equipo de producto.

## 5. Métricas de éxito del MVP
- **Tiempo de creación de agente** ≤ 5 s.
- **Latencia de ejecución de tarea** ≤ 200 ms (99 %).
- **Disponibilidad del API** ≥ 99.5 % en beta.
- **Cobertura de pruebas** ≥ 90 %.
- **Feedback positivo** ≥ 80 % de los usuarios piloto.

---

*Este documento sirve como referencia de planificación y será actualizado conforme se avancen los sprints. Todas las decisiones se versionan mediante el flujo de revisión de documentos de HYDRA.*