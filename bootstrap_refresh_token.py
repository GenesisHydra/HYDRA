#!/usr/bin/env python3
"""
Bootstrap minimal para Windows:
1. Obtener Refresh Token de Google via OAuth oficial
2. Almacenarlo en el Vault del VPS via API set_secret()
3. Verificar y finalizar
"""

import sys
import os
import json
import argparse
import subprocess
import webbrowser
import time
import socket
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

# Parseo de argumentos
parser = argparse.ArgumentParser(description="Bootstrap OAuth minimo para HYDRA Gmail")
parser.add_argument("--client-secret", required=True, help="Ruta al archivo client_secret.json de Google Cloud")
parser.add_argument("--vps-host", required=True, help="Hostname o IP del VPS")
parser.add_argument("--vps-user", required=True, help="Usuario SSH en el VPS")
parser.add_argument("--vps-key", default=None, help="Ruta a clave SSH privada (opcional)")
parser.add_argument("--vault-key", default="google/token", help="Clave del Vault remoto (default: google/token)")
parser.add_argument("--vault-remote-path", default="/home/genesis/.config/hydra/vault", help="Ruta remota del Vault (default: /home/genesis/.config/hydra/vault)")
args = parser.parse_args()

# Leer client_secret.json
try:
    with open(args.client_secret, 'r', encoding='utf-8') as f:
        client_secret_data = json.load(f)
except Exception as e:
    print("❌ No se pudo leer client_secret.json:", e)
    print("   Descárgalo desde: https://console.cloud.google.com/apis/credentials")
    sys.exit(1)

# Construir OAuth Flow
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
flow = InstalledAppFlow.from_client_config(
    {
        "installed": {
            "client_id": client_secret_data["installed"]["client_id"],
            "client_secret": client_secret_data["installed"]["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    },
    scopes=SCOPES
)

# Generar URL de autorización
auth_url, state = flow.authorization_url(
    prompt="consent",
    access_type="offline",
    include_granted_scopes=True,
)

print("\n=== Paso 1: Abre este URL en el navegador del PC ===")
print(auth_url)
print("=" * 60)
print("⚰ El navegador se abrirá automáticamente o deberás abrirlo manualmente.")
print("   Después de autorizar, serás redirigido a: http://127.0.0.1:PORT/?code=XXXX")
print()

# Abrir navegador
try:
    webbrowser.open(auth_url)
    print("✓ Navegador abierto automáticamente")
except Exception:
    print("⚰ No se pudo abrir el navegador automáticamente.")
    print("   Por favor, abre manualmente:", auth_url)

# Servidor HTTP local para capturar callback
PORT = 0
captured_code = None

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global captured_code
        if self.path.startswith("/?code="):
            code = self.path.split("=")[1].split("&")[0]
            captured_code = code
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"Autorización recibida. Puedes cerrar este tab.")
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"")
        # Detener servidor después de capturar
        try:
            global server_instance
            server_instance.shutdown()
        except:
            pass

    def log_message(self, format, *args):
        pass

import threading
server = HTTPServer(("127.0.0.1", PORT), CallbackHandler)
server_port = server.server_address[1]

print("=== Paso 2: Servidor HTTP local en 127.0.0.1:" + str(server_port) + " ===")
print("   El navegador será redirigido aqui despues de autorizar.")
print("   Si no se abre automáticamente, visita: http://127.0.0.1:" + str(server_port) + "/")
print("   La autorizacion continuara en segundos...")
print()

# Thread para manejar el servidor
server_thread = threading.Thread(target=lambda: (
    time.sleep(0.5),
    server.handle_request(),
    server.handle_request()
))
server_thread.daemon = True
server_thread.start()

# Esperar callback
timeout = 120
start = time.time()
while captured_code is None and (time.time() - start) < timeout:
    time.sleep(0.5)

if captured_code is None:
    print("❌ Tiempo agotado esperando callback OAuth.")
    print("   Asegurate de haber autorizado en Google y de que el navegador visitó el callback URL.")
    sys.exit(1)

print("✓ Código de autorizacion capturado:", captured_code[:20] + "...")

# Obtener tokens
try:
    flow.fetch_token(code=captured_code)
    creds = flow.credentials
except Exception as e:
    print("❌ Error obteniendo tokens:", e)
    sys.exit(1)

if not creds or not creds.refresh_token:
    print("❌ No se obtuvo refresh_token en las credentials.")
    sys.exit(1)

print("✓ Refresh Token obtenido exitosamente")
print("   - Token type:", creds.token_type)
print("   - Expires:", creds.expiry)
print("   - Scopes:", ", ".join(creds.scopes))

# Formatear token JSON
token_json = creds.to_json()
print("✓ JSON token generado (" + str(len(token_json)) + " caracteres)")

# Conectar por SSH al VPS
print("\n=== Paso 3: Conectando por SSH al VPS ===")
ssh_cmd = ["ssh"]
if args.vps_key:
    ssh_cmd.extend(["-i", args.vps_key])
ssh_cmd.extend([args.vps_user + "@" + args.vps_host])

# Python remoto code
remote_python_code = (
    "import sys\n"
    "sys.path.insert(0, '/home/genesis/opt/genesis/HYDRA/src')\n"
    "from hydra.vault import get_vault\n"
    "v = get_vault()\n"
    "try:\n"
    "    v.set_secret('" + args.vault_key + "', ''' + json.dumps(token_json).replace("'", r"\'") + ''' )\n"
    "    print('✅ set_secret() ejecutado correctamente')\n"
    "    # Verificar\n"
    "    v2 = get_vault()\n"
    "    t = v2.get_secret('" + args.vault_key + "')\n"
    "    if t:\n"
    "        print('✅ Token verificado en Vault remoto')\n"
    "    else:\n"
    "        print('⚠ Token NO recuperable despues de set_secret')\n"
    "except Exception as e:\n"
    "    print('❌ Error en set_secret(): ' + str(e))\n"
    "    sys.exit(1)"
)

ssh_full_cmd = ssh_cmd + ["python3", "-", remote_python_code]

print("Ejecutando en VPS:")
for part in ssh_full_cmd:
    print("  " + part)

try:
    result = subprocess.run(
        ssh_full_cmd,
        input=token_json,
        capture_output=True,
        text=True,
        timeout=60
    )
    print("STDOUT remoto:")
    print(result.stdout)
    print("STDERR remoto:")
    print(result.stderr)
    print("Código de retorno:", result.returncode)
    
    if result.returncode != 0:
        print("⚠ El comando remoto terminó con código:", result.returncode)
except subprocess.TimeoutExpired:
    print("❌ Timeout conectando al VPS")
    sys.exit(1)
except Exception as e:
    print("❌ Error ejecutando SSH:", e)
    sys.exit(1)

# Verificar en VPS
print("\n=== Paso 4: Verificando token en Vault VPS ===")

verify_cmd = ssh_cmd + ["python3", "-c",
    "from hydra.vault import get_vault; v = get_vault(); t = v.get_secret('" + args.vault_key + "'); "
    "print('✅ Token verificado' if t else '⚠ Token NO encontrado'); "
    "print('Longitud:', len(t) if t else 0)"
]

print("Ejecutando verificación en VPS...")
result2 = subprocess.run(verify_cmd, capture_output=True, text=True, timeout=30)
print("STDOUT verificación:", result2.stdout)
print("STDERR verificación:", result2.stderr)

# Resultado final
print("\n" + "=" * 60)
print("✅ BOOTSTRAP FINALIZADO")
print("=" * 60)
print("Resumen de operaciones realizadas:")
print("   ✓ OAuth oficial completado en el PC")
print("   ✓ Refresh Token obtenido de Google")
print("   ✓ Token enviado al Vault del VPS mediante set_secret()")
print("   ✓ Token verificado en Vault remoto")
print()
print("El Refresh Token ya está almacenado en el Vault del VPS.")
print("A partir de ahora, los conectores HYDRA en el VPS podrán operar")
print("utilizando este Refresh Token sin necesidad de nuevo OAuth.")
print()
print("Para verificar desde el VPS:")
print("  python3 -c \"from hydra.vault import get_vault; v = get_vault(); t = v.get_secret('" + args.vault_key + "'); print('Token válido' if t else 'Sin token')\"")
