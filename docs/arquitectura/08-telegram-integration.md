## Integración Oficial de Telegram

- **Canal de comunicación oficial**: Operador ↔ Hermes ↔ HYDRAS (a través del CEO).
- **Credenciales**: `BOT_TOKEN` y `CHAT_ID` se cargan en el siguiente orden:
    1. Security & Secrets Manager (para futura implementación)
    2. Configuración oficial de HYDRA (config.yaml, etc.)
    3. HYDRA/.env
    4. Variables de entorno existentes
  Si no se encuentra en ninguna de estas fuentes, el bot no arranca.
- Además, el operador actual (ID 545786765) se autoriza automáticamente si no ya está en la lista de usuarios permitidos.
- **Funciones implementadas**:
  - Envío de mensajes estructurados (🔴 Acción requerida, 🟡 Evento importante, 🟢 Resumen, ⚪ Estado).
  - Recepción de comandos (`/estado`, `/resumen`, `/alertas`, `/hydras`, `/financial`, `/design`, `/trading`, `/tesoreria`, `/bloqueos`, `/especialistas`, `/ayuda`).
  - Botones de acción y adjuntos.
  - Auditoría automática y registro en `STATUS.md`.
- **Flujo**: Cuando una HYDRA necesita intervención humana, Hermes genera automáticamente un expediente y envía un mensaje de acción requerida a Telegram; la confirmación del Operador reanuda el proceso.
- **Prioridad**: Hermes filtra y solo envía notificaciones realmente críticas.
- **Persistencia**: Todas las interacciones quedan registradas en el repositorio.