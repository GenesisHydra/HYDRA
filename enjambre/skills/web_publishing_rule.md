# REGLA OBLIGATORIA DE PUBLICACIÓN WEB (HORMIGUITAS)

Queda terminantemente prohibido utilizar comandos manuales de Git (`git commit`, `git push`, `git add` complejos) para actualizar la página web de HYDRA.

Para publicar cualquier cambio, artículo, diseño o actualización en la web pública de forma segura, el único procedimiento autorizado es ejecutar el script automatizado raíz:

\`\`\`bash
./publicar.sh
\`\`\`

Este script se encarga de validar los archivos limpios, ignorar carpetas protegidas (`venv`, `vault`, `.env`) y subir los cambios a GitHub Pages sin errores ni riesgos de seguridad.
