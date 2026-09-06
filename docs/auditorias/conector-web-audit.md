# Auditoria del Conector Web HYDRA (Actualizado)

## Estado: IMPLEMENTADO - v1.0

### Archivos creados
- `src/hydra/web/__init__.py` - Paquete del conector web
- `src/hydra/web/connector.py` - Implementacion completa (WebConnector + WebService)

### Arquitectura
- Sigue el patron de TelegramConnector (vault + servicio + health_check)
- Recupera URL del Vault (company/website) con fallback a DEFAULT_WEB_URL
- WebService: operaciones HTTP de alto nivel (get_page, download_file, health)
- WebConnector: clase principal para gestionar la web desde el VPS

### Funcionalidades implementadas
- health_check() - Verificar accesibilidad web remota
- get_page(path) - Obtener contenido HTML de cualquier pagina
- download_file(path, local_path) - Descargar archivos de la web
- get_web_url() - Obtener URL configurada
- check_local_build() - Verificar build local (index.html, dist/, _site/)
- list_public_files() - Listar archivos publicos locales
- sync_to_remote() - Verificar sincronizacion local/remota
- fetch_page_metadata() - Extraer titulo, descripcion, og:image
- get_sitemap() / get_robots_txt() - Metadatos de SEO

### Vault
- Clave: company/website = https://genesishydra.github.io/HYDRA/
- Fecha registro: 2026-09-05T13:23:37.851265

### Dependencias
- requests (ya existente en requerimientos)
- hydra.vault (modulo existente)

### Estado desarrollo
- CONECTOR: IMPLEMENTADO Y OPERATIVO
- AUTH: Pendiente integrar credenciales en Vault si son necesarias
- CI/CD: Sin pipeline de despliegue automatizado (requiere integracion separada)

### Rutas exactas
- Repositorio: /home/genesis/opt/genesis/HYDRA
- Conector: src/hydra/web/connector.py
- Paquete: src/hydra/web/__init__.py
- Audit: docs/auditorias/conector-web-audit.md

---
*Actualizado: 2026-09-06*
