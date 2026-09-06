# Auditoría del Conector Web HYDRA

## Estado actual: SIN IMPLEMENTAR

### 1. Nombre y dominio
- Web/project: `https://genesishydra.github.io/HYDRA/`
- Dominio/Proyecto: HYDRA

### 2. Tecnología y ubicación
- No existe un conector de web dedicado en el código fuente
- El dominio está registrado como secret `company/website` en el Vault de HYDRA (`/home/genesis/opt/genesis/config/vault/secrets.enc`)
- Tecnología: Static site generator (GitHub Pages) basado en el contenido de `_site/`, `dist/`, `banners/`, `lib/`

### 3. Fecha de creación
- Primera referencia: `2026-09-05T13:23:37.851265` (cuando se guardó `company/website` en el Vault)
- Actividad inicial en vault: `2026-09-05T09:13:55.737674` (credenciales Telegram)

### 4. Despliegue / Publicación
- Proveedor: GitHub Pages
- URL pública: `https://genesishydra.github.io/HYDRA/`
- Estado: Activa y accesible
- El vault **no** almacena credenciales de despliegue (solo la URL destino)

### 5. Flujo de sincronización actual
- No hay scripts de integración entre el vault y GitHub Pages
- El contenido del sitio se genera/actualiza manualmente o mediante flujo CI/CD externo
- Los únicos datos sincronizados son la URL objetivo (`company/website`) y credenciales Telegram

### 6. Conectores relacionados (existentes)
- `TelegramConnector` (`src/hydra/telegram/connector.py`) – completamente implementado y operativo
- `GmailConnector` (`src/hydra/google/gmail/gmail_connector.py`) – implementado con OAuth 2.0
- No existe `WebConnector` o similar

### 7. Estado de avance dentro del plan global de conectores
- El conector web está **pendiente** (no comienza)
- Tipo: Extensión de conector (según ARCHITECTURE.md §5 – "Connector implementations are extensions")
- Próximos pasos esperados:

### 8. Hallazgos críticos
- El vault contiene la URL objetivo pero no hay código que la consuma o valida
- No hay endpoints API ni flujos de sincronización web definidos
- El proyecto necesita un conector web para completar el ecosistema de conectores de HYDRA

---
*Informe generado el 2026-09-06. Para consultas: revisar ARCHITECTURE.md y el patrón de TelegramConnector.*
