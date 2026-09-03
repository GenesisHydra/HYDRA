# HYDRA Identity Manager (HIM)

## Visión
Gestiona identidades digitales de cada instancia HYDRA con generación automática de IDs, correos, dominios, wallets, API keys, OAuth, secretos y credenciales. Todas las operaciones son auditables, cifradas y rotativas.

## Componentes
- **Modelo** (`models.py`): estructuras Pydantic para identidad, credenciales y wallets.
- **Servicio** (`service.py`): creación, consulta, suspensión, cierre, rotación de credenciales, gestión de wallets y auditoría.
- **Almacén seguro**: placeholder `_STORAGE` que en producción será reemplazado por Vault/KMS.
- **API**: se expondrá vía FastAPI en futuros pasos (router pendiente).

## Ciclo de vida
1. **Nacimiento** – `create_identity` genera ID inmutable y metadatos.
2. **Operación** – uso de credenciales, wallets y API keys.
3. **Actualización** – rotación de credenciales, actualización de metadata.
4. **Suspensión** – `suspend_identity` bloquea operaciones.
5. **Cierre** – `close_identity` marca como cerrada.
6. **Recuperación de activos** – exporta wallets, API keys y dominios antes de borrado.

## Seguridad
- Cifrado de secretos (placeholder `enc-` a sustituir por KMS).
- Rotación automática mediante `rotate_credential`.
- Auditoría completa (`audit_log`).
- Principio de mínimo privilegio en cada operación.

## Integración con HYDRA
- Cada nueva HYDRA invoca `create_identity` al iniciar.
- Los módulos internos consumen credenciales mediante `get_identity` y `create_credential`.
- El Document Mother se actualiza con referencia a HIM como componente obligatorio.
