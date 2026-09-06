#!/usr/bin/env python3
"""
Deploy script para la web HYDRA.
Sube el index.html modificado a GitHub Pages mediante git.
"""
import subprocess
import sys
import os

def deploy_to_github_pages():
    """Despliega los cambios a gh-pages usando git checkout y push."""
    repo_dir = "/home/genesis/opt/genesis/HYDRA"
    os.chdir(repo_dir)
    
    # Verificar que estamos en la rama gh-pages
    try:
        result = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True)
        current_branch = result.stdout.strip()
        print(f"Rama actual: {current_branch}")
    except Exception as e:
        print(f"Error al obtener rama: {e}")
        return False
    
    # Si no estamos en gh-pages, necesitamos hacer checkout del archivo
    # Pero como el proyecto usa gh-pages como rama de despliegue, copiamos el archivo allí
    
    # Leer el index.html actual de gh-pages (si existe)
    gh_pages_index = os.path.join(repo_dir, "index.html")
    
    # Realizar commit de los cambios
    try:
        # Agregar cambios
        subprocess.run(["git", "add", "index.html"], check=True)
        
        # Commit con mensaje
        subprocess.run([
            "git", "commit", "-m",
            "feat(web): Agregar ojo destacado en portada - conector web activo"
        ], check=True)
        
        # Push a gh-pages
        subprocess.run(["git", "push", "origin", "gh-pages"], check=True)
        
        print("Deploy exitoso a GitHub Pages")
        return True
        
    except subprocess.CalledProcessError as e:
        if "nothing to commit" in str(e):
            print("No hay cambios que commitear")
        else:
            print(f"Error en deploy: {e}")
        return False

if __name__ == "__main__":
    success = deploy_to_github_pages()
    sys.exit(0 if success else 1)
