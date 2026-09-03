# HYDRA Capability Manager (HCM)

## Visión
El HCM es el pilar central que gestiona y controla el acceso a todas las capacidades operativas del ecosistema HYDRA (APIs externas, MCPs, herramientas, plugins, SDKs, modelos IA, etc.). Cada HYDRA solicita temporalmente los recursos que necesita; el HCM evalúa, autoriza, instala, configura y audita el uso.

## Arquitectura
- **Catálogo de capacidades** (`models.Capability`): ID único, nombre, descripción, tipo, proveedor, coste, dependencias, nivel de riesgo, estado, versiones, permisos requeridos y lista de HYDRAS autorizadas.
- **Servicios** (`service.py`): 
  - `register_capability` – alta de nuevas capacidades.
  - `list_capabilities` – consulta del catálogo.
  - `request_capability` – HYDRA solicita una capacidad.
  - `allocate_capability` – HYDRA CORE aprueba/rechaza la solicitud, actualiza autorización.
  - `revoke_capability` – revoca acceso.
  - `_audit` – registro inmutable de todas las operaciones.
- **Almacén** – `_STORE` placeholder (en producción se sustituirá por una base de datos cifrada y persistente).

## Ciclo de vida de una capacidad
1. **Registro** – un administrador del ecosistema publica la capacidad en el catálogo.
2. **Solicitud** – la HYDRA envía un `CapabilityRequest` con motivos y permisos.
3. **Evaluación** – HYDRA CORE decide (puede incluir lógica de coste, riesgo, disponibilidad).
4. **Asignación** – `allocate_capability` crea una `CapabilityAllocation`; si se aprueba, la HYDRA queda listada en `authorized_hydras`.
5. **Activación** – la infraestructura (orquestador) instala/configura la herramienta bajo sandbox/min‑privilege.
6. **Uso** – la HYDRA consume la capacidad; cada uso se registra.
7. **Revocación** – el HCM puede retirar la autorización (revocación automática al fin de la suscripción o por riesgo).
8. **Eliminación** – capacidad retirada del catálogo cuando está obsoleta.

## Seguridad
- Principio de **mínimo privilegio**: las capacidades se ejecutan en contenedores/sandboxes.
- **Cifrado** de credenciales y tokens almacenados.
- **Rotación** automática de tokens mediante `rotate_credential` del HIM.
- **Auditoría completa** (`audit_log`) con timestamps, eventos y metadatos.
- **Control de costos**: cada capacidad lleva un coste estimado; el HCM puede limitar el gasto por HYDRA.

## Integración
- **HYDRA CORE**: orquesta decisiones de autorización.
- **HIM**: provee credenciales y secretos necesarios para la capacidad.
- **Knowledge Manager**: actualiza la documentación de capacidades.
- **Capital Manager**: evalúa coste de contratar una capacidad.
- **Evolution Engine**: adapta el catálogo a nuevas tendencias.

## Operación
- Cada HYDRA, al iniciar, consulta el HCM para obtener la lista de capacidades autorizadas.
- Para usar una nueva API o herramienta, envía `request_capability`; tras la aprobación, la infraestructura crea los recursos necesarios (por ejemplo, provisiona una cuenta en AWS, genera una API‑key o despliega un contenedor con la herramienta).
- Todas las acciones quedan registradas en `audit_log`, garantizando trazabilidad y cumplimiento.

## Escalabilidad
- Catalogación basada en IDs permite gestionar **miles de capacidades**.
- Autorizaciones almacenadas como listas en cada `Capability` permiten **miles de HYDRAS** simultáneas.
- El diseño modular permite distribuir la lógica de servicio en micro‑servicios y escalar horizontalmente mediante FastAPI + Kubernetes.

## Roadmap
- Exponer API FastAPI (`router/capability.py`) para que HYDRA CORE y las HYDRAS interactúen.
- Sustituir `_STORE` por una base de datos cifrada (Postgres + pgcrypto, o Vault).
- Implementar sandboxing automático (Docker, Firecracker) para ejecutar herramientas.
- Integrar métricas de coste y alertas de riesgo.
- Añadir versiones de capacidades y gestión de dependencias.

---
*Este documento forma parte del repositorio HYDRA y se actualizará con cada iteración del HCM.*