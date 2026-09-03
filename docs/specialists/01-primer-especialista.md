# Primer Especialista: Financial Summary SaaS

## Propósito
Especialista autónomo dedicado al dominio **Financial Summary SaaS** (micro‑SaaS de resúmenes financieros). Su objetivo es investigar el mercado, generar oportunidades de inversión y enviarlas al Investment Board.

## Identidad
- ID generado por HIM al crear el especialista.
- Metadatos: dominio = `financial-summary-saas`.

## Capacidades solicitadas
- Web Search (API, permiso `internet`).
- HTTP Client (tool, permiso `network`).
- Data Analysis (library `pandas`).

## Flujo de trabajo
1. `launch_specialist` registra identidad y capacidades vía HIM y HCM.
2. Se inicia un sub‑agente que ejecuta `run_cycle` perpetuamente (en demo una iteración).
3. `run_cycle`:
   - Investiga (simulado con insight estático).
   - Evalúa la oportunidad, calcula un score y genera una propuesta.
   - Persiste la propuesta en la cola `investment_board_queue.jsonl`.
   - Actualiza su memoria y métricas.
4. El Investment Board consumirá la cola y HYDRA CORE decidirá.

## Persistencia
- Estado del especialista (`<BASE>/data/specialists/<specialist_id>.json`).
- Cola de propuestas (`<BASE>/data/investment_board_queue.jsonl`).

## Evolución
Cada ciclo persiste insights y mejoras; la versión del skill de investigación se actualizará automáticamente mediante el motor de evolución de HOI.

---
*Este documento forma parte del repositorio HYDRA y refleja la arquitectura oficial del ecosistema de especialistas.*