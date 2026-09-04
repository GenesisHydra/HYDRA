## Estado actual y próximos pasos para publicar GenesisHydra en GitHub Pages

1. Falta generar archivos HTML estáticos a partir de las plantillas Jinja2 y publicar esa carpeta estática mediante el workflow de GitHub Actions (actualmente solo valida la app sin build).
2. Tiempo estimado: 2 horas para crear un script de renderizado estático y ajustar el despliegue.
3. El dominio debe comprarse y configurarse después de verificar que el sitio funciona bajo el subdominio github.io, luego se añade el CNAME en Settings > Pages.
4. Es recomendable usar un Gmail temporal durante el desarrollo y cambiar al correo corporativo una vez se tenga el dominio configurado.
5. Estrategia profesional:
   - Comprar dominio (genesishydra.com o similar)
   - Configurar correos corporativos (contacto@..., hello@..., etc.)
   - Crear repositorio GitHub y habilitar GitHub Pages con sitio estático
   - Publicar sitio y validar
   - Crear perfiles en LinkedIn, X (Twitter), YouTube, Instagram, Facebook, Discord y Telegram, todos vinculando al dominio y al sitio.
6. Tareas automáticas: renderizado de HTML estático, despliegue vía GitHub Actions, actualización de CNAME mediante workflow (opcional). Tareas que requieren intervención: compra de dominio, creación de cuentas de correo y redes sociales, rellenado de contenido inicial y verificación de despliegue.

Informe guardado en /home/genesis/opt/genesis/HYDRA/REPORT.md