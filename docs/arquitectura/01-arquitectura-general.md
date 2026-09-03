# Arquitectura General del Software HYDRA

## Visión Global
La plataforma HYDRA es un ecosistema de agentes de IA gestionado por **HYDRA CORE** que actúa como cerebro central, controla el **Fondo HYDRA**, y supervisa la creación y operación de las **HYDRAS hijas**. La arquitectura debe ser **modular**, **extensible**, **segura**, y **orientada a eventos**, permitiendo añadir nuevas HYDRAS, integrar servicios externos y escalar horizontalmente.

---

## Principios de Arquitectura
1. **Separación de responsabilidades (Clean/Hexagonal Architecture).**
2. **Domain‑Driven Design (DDD):** Cada sub‑dominio (Capital, Inversión, Gobernanza, Operaciones) tiene su propio modelo de dominio y casos de uso.
3. **Event‑Driven & CQRS:** Cambios críticos (p. ej. asignación de capital) se publican como eventos y son procesados por lectores independientes.
4. **Reutilización mediante componentes y patrones comunes:**
   - *Factory*, *Strategy*, *Observer*, *Decorator*.
5. **Escalabilidad horizontal:** Servicios stateless se despliegan en contenedores/Kubernetes; los datos críticos permanecen en fuentes de datos persistentes.
6. **Seguridad por diseño:** Autenticación de agentes vía tokens firmados, autorización basada en roles, auditoría de todas las transacciones.

---

## Módulos Principales
| Módulo | Responsabilidad | Principales Interfaces | Patrones Reutilizados |
|--------|------------------|------------------------|-----------------------|
| **CORE** | Orquesta la lógica de negocio global y expone la API pública. | `ICoreService`, `IEventBus` | Singleton, Facade |
| **Fondo HYDRA** | Gestiona capital, reservas, flujos de caja. | `ICapitalRepository`, `ICapitalAllocator` | Repository, Strategy |
| **Gestión de HYDRAS** | Creación, cierre, replicación y supervisión de HYDRAS hijas. | `IHydraFactory`, `IHydraRegistry` | Factory, Composite |
| **Inversión & Viabilidad** | Evalúa propuestas, calcula métricas de viabilidad, ejecuta aprobaciones. | `IInvestmentEngine`, `IViabilityChecker` | Strategy, Template Method |
| **Auditoría & Reporting** | Registra acciones, genera informes, soporta auditorías externas. | `IAuditLog`, `IReportGenerator` | Observer, Builder |
| **API & Puerta de Entrada** | Exposición REST/GraphQL + WebSocket para agentes y UI. | `IHttpController`, `IWebSocketHandler` | Adapter, Proxy |
| **Persistencia** | Almacena estado de capital, HYDRAS, eventos. | `IDataSource`, `IEventStore` | Repository, Unit‑of‑Work |
| **Seguridad** | Autenticación/ autorización de agentes y usuarios humanos. | `IAuthProvider`, `IAuthorizationService` | Decorator, Chain of Responsibility |
| **Plugin System** | Extiende la plataforma con módulos de dominio o integraciones externas. | `IPlugin`, `IPluginManager` | Plugin, Dependency Injection |

---

## Interfaces Clave (Ejemplo)
```go
// Core Service (exposed to external callers)
type ICoreService interface {
    RegisterHydra(req RegisterHydraRequest) (HydraID, error)
    AllocateCapital(req CapitalAllocationRequest) (AllocationID, error)
    SubmitInvestmentProposal(req InvestmentProposal) (ProposalID, error)
    GetAuditLog(filter AuditFilter) ([]AuditEntry, error)
}

// Capital Allocator (Strategy pattern)
type ICapitalAllocator interface {
    Allocate(ctx context.Context, amount Money, target Target) (AllocationResult, error)
    SetStrategy(s AllocationStrategy)
}
```
*(Los lenguajes pueden ser Go, Rust, TypeScript; la interfaz lógica es independiente del lenguaje.)*

---

## Flujo de Trabajo Típico
1. **Propuesta de Inversión** → `IInvestmentEngine.Evaluate()` → genera `ViabilityReport`.
2. **Aprobación por CORE** → `ICoreService.SubmitInvestmentProposal()` → evento `InvestmentApproved` en `IEventBus`.
3. **Asignación de Capital** → `ICapitalAllocator.Allocate()` → persiste en `IDataSource` y dispara `CapitalAllocated`.
4. **Creación de HYDRA Hija** → `IHydraFactory.Create()` → registro en `IHydraRegistry`.
5. **Auditoría** → `IAuditLog.Record()` captura cada paso.
6. **Reportes** → `IReportGenerator.Generate()` produce documentos Markdown/PDF para la auditoría estratégica.

---

## Componentes Reutilizables
- **EventBus (async pub/sub)** – Implementado con Kafka o NATS.
- **CapitalAllocator** – Múltiples estrategias (`ProRata`, `Priority`, `RiskWeighted`).
- **ViabilityChecker** – Motor de reglas que evalúa los criterios de la sección 5‑7 del Documento Madre.
- **PluginManager** – Carga dinámicamente paquetes `*.so`/`npm` y los registra en el contenedor DI.
- **AuditLog** – Almacén immutable (append‑only) con hash de cadena para integridad.
- **Security Middleware** – Validación JWT firmados por `HYDRA CORE` y verificación de scopes.

---

## Tecnologías Sugeridas
| Capa | Tecnologías | Comentario |
|------|--------------|------------|
| **API** | FastAPI (Python) o NestJS (TypeScript) | endpoints REST + WebSocket |
| **Persistencia** | PostgreSQL + TimescaleDB (event store) | ACID + series temporales |
| **Mensajería** | NATS Streaming o Apache Kafka | bajo acoplamiento, alta disponibilidad |
| **Contenedores** | Docker + Kubernetes | despliegue escalable |
| **Seguridad** | OAuth2 + OPA (Open Policy Agent) | autorización centralizada |
| **CI/CD** | GitHub Actions + ArgoCD | pipelines declarativos |
| **Observabilidad** | Prometheus + Grafana + Loki | métricas, logs y trazas |

---

## Diagramas (referencia externa)
- **Arquitectura Hexagonal** – muestra puertos (API, EventBus, Plugin) y adaptadores (DB, Kafka, UI).
- **Diagrama de Secuencia** – proceso de creación de una HYDRA hija.
- **Mapa de Dependencias** – módulos y sus relaciones.

*(Los diagramas pueden generarse con `architecture-diagram` skill y guardarse en `docs/arquitectura/diagrams/`.)*

---

## Roadmap de Implementación
| Sprint | Objetivo | Entregable |
|--------|----------|------------|
| 1 | Infraestructura básica (API, EventBus, DB) | Repositorio `hydra-core` con CI y despliegue local |
| 2 | Módulo Fondo HYDRA + CapitalAllocator | Servicios `core/capital/*` y pruebas unitarias |
| 3 | Gestión de HYDRAS + Plugin System | API `registerHydra`, `listHydras`, carga de plugins |
| 4 | Auditoría y Reporting | `audit/*` con generación de Markdown/PDF |
| 5 | Seguridad y autorización | JWT + OPA policies, pruebas de penetración |
| 6 | Escalado y observabilidad | Deploy en Kubernetes, dashboards Prometheus |

---

## Conclusión
Esta arquitectura modular, basada en patrones probados y orientada a eventos, satisface los requisitos del **Documento Madre** y de la **Auditoría Estratégica Global**. Permite a **HYDRA CORE** mantener el control central del fondo, mientras que las HYDRAS hijas pueden ser creadas, evaluadas y cerradas de forma automatizada y auditable. La siguiente fase será materializar los diagramas y comenzar la implementación del sprint 1.
