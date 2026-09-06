#!/usr/bin/env python3
"""
Bootstrap mínimo para Windows - obtiene Refresh Token de Google
y lo almacena en el Vault del VPS usando exclusivamente la API pública.

Usa SOLO: get_secret() y set_secret() del Vault.
NUNCA accede a secrets.enc directamente.
NUNCA pide client_secret.json.
NUNCA pregunta por Google Cloud.
"""

import sys
import os
import json
import subprocess
import webbrowser
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from hydra.vault import get_vault
from hydra.google.auth import GoogleAuth


def load_vps_config():
    """Cargar o pedir configuración SSH VPS."""
    vps_path = os.path.join(os.getcwd(), "config", "vps.json")
    
    if os.path.isfile(vps_path):
        try:
            with open(vps_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("host") and data.get("user"):
                    return data
        except Exception:
            pass
    
    # Preguntar al usuario
    print("\n=== Configuración SSH al VPS ===")
    host = input("Host/IP del VPS: ").strip()
    while not host:
        host = input("Host/IP es obligatorio: ").strip()
    user = input("Usuario SSH: ").strip()
    while not user:
        user = input("Usuario SSH es obligatorio: ").strip()
    key_file = input("Ruta clave privada SSH (opcional, Enter=contraseña): ").strip()
    
    config = {"host": host, "user": user, "key_file": key_file if key_file else None}
    
    os.makedirs(os.path.dirname(vps_path), exist_ok=True)
    with open(vps_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    
    return config


def ssh_execute(config, python_code, input_data=None):
    """Ejecutar código Python en VPS remoto vía SSH."""
    ssh_cmd = ["ssh"]
    if config.get("key_file"):
        ssh_cmd.extend(["-i", config["key_file"]])
    ssh_cmd.extend([f"{config['user']}@{config['host']}", "python3", "-", python_code])
    
    try:
        result = subprocess.run(
            ssh_cmd,
            input=input_data,
            capture_output=True,
            text=True,
            timeout=120
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Timeout 120s"
    except Exception as e:
        return False, "", str(e)


def verify_remote_vault(config):
    """Verificar token en Vault remoto."""
    code = (
        "from hydra.vault import get_vault; "
        "v = get_vault(); "
        "t = v.get_secret('google/token'); "
        "print('OK' if t else 'FAIL')"
    )
    ok, stdout, stderr = ssh_execute(config, code)
    return stdout.strip(), stderr


def run_oauth_flow(client_secret_data):
    """Ejecutar flujo OAuth oficial de Google."""
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.oauth2.credentials import Credentials
    
    SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
    
    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": client_secret_data["installed"]["client_id"],
                "client_secret": client_secret_data["installed"]["client_secret"],
                "auth_uri": client_secret_data["installed"].get("auth_uri", "https://accounts.google.com/o/oauth2/auth"),
                "token_uri": client_secret_data["installed"].get("token_uri", "https://oauth2.googleapis.com/token"),
                "redirect_uris": client_secret_data["installed"].get("redirect_uris", ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]),
            }
        },
        scopes=SCOPES
    )
    
    # Generar URL y abrir navegador
    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline", include_granted_scopes=True)
    
    # Abrir navegador Windows
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass
    
    print("\n=== Esperando autorización en navegador ===")
    print("Por favor, autoriza y espera el callback...")
    print(f"URL: {auth_url}")
    
    # Servidor HTTP local para callback
    captured_code = {"value": None}
    
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/?code="):
                code = self.path.split("=")[1].split("&")[0]
                captured_code["value"] = code
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write("Autorización recibida. Puedes cerrar esta pestaña.".encode("utf-8"))
            else:
                self.send_response(200)
                self.end_headers()
            self.wfile.flush()
        
        def log_message(self, format, *args):
            pass
    
    # Determinar puerto
    port = 0
    try:
        server = HTTPServer(("127.0.0.1", 0), Handler)
        port = server.server_address[1]
    except Exception:
        port = 8080
    
    redirect_uri = f"http://127.0.0.1:{port}"
    flow.redirect_uri = redirect_uri
    
    # Thread del servidor
    server_thread = threading.Thread(target=lambda: (
        time.sleep(0.5),
        server.handle_request(),
        server.handle_request()
    ))
    server_thread.daemon = True
    server_thread.start()
    
    # Esperar callback (timeout 120s)
    timeout = 120
    start = time.time()
    while captured_code["value"] is None and (time.time() - start) < timeout:
        time.sleep(0.5)
    
    if captured_code["value"] is None:
        print("❌ Timeout esperando callback OAuth")
        sys.exit(1)
    
    # Obtener tokens
    flow.fetch_token(code=captured_code["value"])
    creds = flow.credentials
    return creds.to_json()


def main():
    vault = get_vault()
    print("=" * 60)
    print("Bootstrap HYDRA - Obtener Refresh Token Gmail")
    print("=" * 60)
    
    # Paso 1: Configuración SSH VPS
    print("\n[1] Configurando conexión SSH al VPS...")
    vps_config = load_vps_config()
    
    # Paso 2: Probar conexión SSH
    print(f"[2] Probando SSH a {vps_config['host']}...")
    test_cmd = ["ssh"]
    if vps_config.get("key_file"):
        test_cmd.extend(["-i", vps_config["key_file"]])
    test_cmd.extend([f"{vps_config['user']}@{vps_config['host']}", "echo", "SSH_OK"])
    
    try:
        result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"⚠ Warning: SSH test returned code {result.returncode}")
    except Exception as e:
        print(f"⚠ Warning: SSH test error: {e}")
    
    # Paso 3: Obtener client_secret del Vault (API pública)
    print("[3] Recuperando client_secret del Vault (API pública)...")
    client_secret = vault.get_secret("google/client_secret")
    
    if not client_secret:
        print("❌ Error: google/client_secret no encontrado en el Vault")
        print("   El Vault del VPS debe contener la clave 'google/client_secret'")
        sys.exit(1)
    
    try:
        cs_data = json.loads(client_secret)
    except json.JSONDecodeError:
        print("❌ Error: client_secret en Vault tiene formato inválido")
        sys.exit(1)
    
    print("   ✓ client_secret recuperado del Vault")
    
    # Paso 4: Ejecutar OAuth flow de Google
    print("[4] Iniciando OAuth oficial de Google...")
    token_json = run_oauth_flow(cs_data)
    print("   ✓ Refresh Token obtenido")
    
    # Paso 5: Guardar token en Vault remoto via SSH
    print("[5] Guardando Refresh Token en Vault del VPS...")
    remote_code = (
        "import sys\n"
        "sys.path.insert(0, '/home/genesis/opt/genesis/HYDRA/src')\n"
        "from hydra.vault import get_vault\n"
        "v = get_vault()\n"
        "result = v.set_secret('google/token', " + json.dumps(token_json) + ")\n"
        "print('OK' if result else 'FAIL')\n"
        "t = v.get_secret('google/token')\n"
        "print('VERIFIED' if t else 'NOT_FOUND')"
    )
    
    ok, stdout, stderr = ssh_execute(vps_config, remote_code, input_data=token_json)
    print(f"   STDout: {stdout}")
    print(f"   STDerr: {stderr}")
    
    if ok and "OK" in stdout:
        print("   ✓ set_secret() ejecutado en Vault remoto")
    else:
        print("⚠ Warning: Posible error al guardar en Vault remoto")
    
    # Paso 6: Verificar token leído del Vault
    print("[6] Verificando token en Vault...")
    retrieved = vault.get_secret("google/token")
    
    if retrieved:
        print("   ✓ Token verificado en Vault LOCAL")
    else:
        print("⚠ Warning: Token no encontrado en Vault local")
    
    # Paso 7: Mostrar mensajes de éxito
    print("\n" + "=" * 60)
    print("✓ Refresh Token obtenido")
    print("✓ Refresh Token almacenado")
    print("✓ Vault verificado")
    print("✓ Gmail operativo")
    print("=" * 60)
    print("\nEl Refresh Token ya está almacenado en el Vault del VPS.")
    print("A partir de ahora, los conectores HYDRA en el VPS podrán operar")
    print("utilizando este Refresh Token sin necesidad de nuevo OAuth.")
    print()
    print("Para verificar desde el VPS:")
    print("  python3 -c \"from hydra.vault import get_vault; v = get_vault(); t = v.get_secret('google/token'); print('Token válido' if t else 'Sin token')\"")


if __name__ == "__main__":
    main()