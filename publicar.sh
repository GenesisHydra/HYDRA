#!/bin/bash
echo "🐜 [Hormiguitas Publisher] Iniciando despliegue automatizado..."

# 1. Asegurar que estamos en gh-pages y actualizados
git checkout gh-pages > /dev/null 2>&1

# 2. Añadir solo archivos seguros y la web (ignorando venv, vault y .env automáticamente)
git add public/ index.html .gitignore

# 3. Comprobar si hay cambios reales para subir
if git diff --cached --quiet; then
    echo "⚠️ No hay cambios nuevos en los archivos web para publicar."
    exit 0
fi

# 4. Hacer commit y push limpio
git commit -m "auto: publicacion rapida de contenido web por agente"
git push origin gh-pages

echo "🚀 ¡Despliegue completado con éxito! La web está actualizada."
