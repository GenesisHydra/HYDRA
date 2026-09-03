# HYDRA Specialists Architecture

## Visión
El nuevo ecosistema de especialistas está compuesto por agentes ultra‑especializados (TikTok, FastAPI, Stripe, etc.) que operan en ciclos infinitos de investigación, aprendizaje, experimentación y generación de propuestas. Cada especialista posee su propia memoria persistente y nunca desaparece.

## Arquitectura
- **Paquete `specialists`** bajo `src/specialists/` con `__init__.py`, `models.py` y `service.py`.
- **Modelo `Specialist`**: ID único, dominio de expertise, metadatos y timestamp del último ciclo.
- **Modelo `Proposal`**: propuesta generada por un especialista, con puntuación estimada y estado.
- **Servicio (`service.py`)** implementa registro de especialistas, ciclo de operación (stub), generación de propuestas y cola de envío al Investment Board.
- **Cola de propuestas**: estructura en‑memoria `_STORE["proposals"]` que será consumida por el Investment Board.
- **Persistencia**: actualmente placeholder `_STORE`; en producción será reemplazado por una base de datos cifrada y un motor de eventos.

## Flujo de trabajo
1. Un especialista se registra (`register_specialist`).
2. Un proceso de background ejecuta `run_cycle` infinito (simulado) que:
   - investiga fuentes configuradas en su metadata,
   - aprende y actualiza su memoria,
   - crea una `Proposal` y la inserta en la cola.
3. El **Investment Board** (rediseñado a partir del HOI) consume la cola, evalúa las propuestas y las envía a HYDRA CORE.
4. HYDRA CORE decide crear o no una nueva HYDRA basada en la oportunidad aprobada.

## Escalabilidad
- Cada especialista es un micro‑servicio independiente que puede escalar horizontalmente.
- El registro y la cola usan identificadores únicos, permitiendo miles de especialistas y miles de HYDRAS simultáneas.
- La arquitectura está basada en eventos y en una capa de mensajería (por ejemplo, RabbitMQ/Kafka) que se integrará en etapas posteriores.

## Seguridad
- Cada especialista solo tiene permiso para acceder a los recursos de su dominio.
- Todas las acciones se auditán vía `_audit`.
- Los secretos y credenciales son provisionados por el **HYDRA Identity Manager (HIM)** y no se almacenan en texto plano.

---
*Este documento forma parte del repositorio HYDRA y se actualizará con cada iteración del ecosistema de especialistas.*