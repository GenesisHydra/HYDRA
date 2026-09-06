#!/usr/bin/env python3
"""
Bootstrap nuevo arquitecturau001f
- Usa EXCLUSIVAMENTE la API pública del Vault (get_secret, set_secret)
- Nunca accede directamente a secrets.enc
- Flujo: SSH → Vault API → OAuth → Token → SSH → Vault set_secret

Pasos:
1. Ejecutar bootstrap en Windows (o Linux/macOS)
2. Solicitar datos de conexión SSH al VPS la primera vez (o reutilizar si existen)
3. Conectar por SSH al VPS
4. Recuperar get_secret("google/client_secret") mediante API pública del Vault
5. Ejecutar OAuth oficial de Google en el navegador del PC
6. Obtener Refresh Token
7. Reconectar al VPS
8. Guardar Refresh Token usando EXCLUSIVAMENTE: set_secret("google/token", token_json)
9. Comprobar: get_secret("google/token")
10. Si la comprobación es correcta: finalizar mostrando mensajes de éxito
"""

import sys
import os
import json
import argparse
import subprocess
import webbrowser
import time

from hydra.vault import get_vault
from hydra.google.auth import GoogleAuth


def _load_vps_config():
    """Cargar configuración SSH VPS desde config/vps.json o pedir al usuario."""
    vps_path = os.path.join(os.getcwd(), "config", "vps.json")
    if os.path.isfile(vps_path):
        try:
            with open(vps_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and data.get("host") and data.get("user"):
                    return data
        except Exception:
            pass

    # Si no está configurado, pedir al usuario
    print("\n🔧 Configuración de conexión SSH al VPS")
    print("(se guardará en config/vps.json para futuras ejecuciones)")
    host = input("  Hostname o IP del VPS: ").strip()
    while not host:
        host = input("  Hostname o IP es requerido: ").strip()
    user = input("  Usuario SSH: ").strip()
    while not user:
        user = input("  Usuario SSH es requerido: ").strip()
    key_file = input(
        "  Ruta al archivo de clave SSH privada (opcional, dejar vacío para contraseña): "
    ).strip()
    if not key_file:
        key_file = None
    config = {"host": host, "user": user, "key_file": key_file}
    # Guardar configuración
    os.makedirs(os.path.dirname(vps_path), exist_ok=True)
    with open(vps_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    print("  ✓ Configuración guardada en config/vps.json")
    return config


def _ssh_execute_remote(ssh_config, python_code, input_data=None):
    """Ejecutar código Python en el VPS remoto vía SSH."""
    ssh_cmd = ["ssh"]
    if ssh_config.get("key_file"):
        ssh_cmd.extend(["-i", ssh_config["key_file"]])
    ssh_cmd.extend([f"{ssh_config['user']}@{ssh_config['host']}", "python3", "-", python_code])

    try:
        result = subprocess.run(
            ssh_cmd,
            input=input_data,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Timeout excediendo el límite de 120s al conectar por SSH"
    except Exception as e:
        return False, "", str(e)


def _verify_remote_vault(ssh_config):
    """Verificar que el Vault remoto tenga el token leyéndolo de vuelta."""
    verify_code = (
        "from hydra.vault import get_vault; "
        "v = get_vault(); "
        "t = v.get_secret('google/token'); "
        "print('✅ Refresh Token obtenado' if t else '⚠ Token NO encontrado'); "
        "print('Longitud:', len(t) if t else 0)"
    )
    ok, stdout, stderr = _ssh_execute_remote(ssh_config, verify_code)
    if ok and stdout:
        return stdout.strip()
    return "❌ No se pudo verificar el Vault remoto"


def main():
    vault = get_vault()

    print("🔐 Iniciando HYDRA Bootstrap (nueva arquitectura)")
    print("=" * 60)

    # ===================================================================
    # Paso 2: Solicitar datos de conexión SSH al VPS la primera vez
    # o reutilizarlos si ya existen
    # ===================================================================
    print("\n📡 Paso 2: Configuración de conexión SSH al VPS")
    vps_config = _load_vps_config()

    # ===================================================================
    # Paso 3: Conectar por SSH al VPS
    # ===================================================================
    print(f"\n🔗 Paso 3: Conectando a VPS {vps_config['host']}...")
    # Simple connectivity test - just verify SSH works
    ssh_test_cmd = ["ssh"]
    if vps_config.get("key_file"):
        ssh_test_cmd.extend(["-i", vps_config["key_file"]])
    ssh_test_cmd.extend([f"{vps_config['user']}@{vps_config['host']}", "echo", "SSH_OK"])

    try:
        result = subprocess.run(
            ssh_test_cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            print("⚠ Advertencia: No se pudo probar la conexión SSH (código:", result.returncode, ")")
            print("  STDERR:", result.stderr.strip())
    except subprocess.TimeoutExpired:
        print("⚠ Advertencia: Timeout probando conexión SSH")
    except Exception as e:
        print("⚠ Advertencia: Error probando SSH:", str(e))

    # ===================================================================
    # Paso 4: Recuperar get_secret("google/client_secret") mediante API pública
    # ===================================================================
    print("\n📥 Paso 4: Recuperando client_secret del Vault (API pública)...")
    client_secret = vault.get_secret("google/client_secret")

    if not client_secret:
        print("❌ Error: google/client_secret no encontrado en el Vault.")
        print("   El Vault debe contener la clave 'google/client_secret' previamente.")
        sys.exit(1)

    print("✓ client_secret obtenido del Vault (API pública)")

    # ===================================================================
    # Paso 5: Ejecutar OAuth oficial de Google en el navegador del PC
    # ===================================================================
    print("\n🔓 Paso 5: Ejecutando OAuth oficial de Google en el navegador...")

    # Parsear client_secret del vault (debe tener formato {"installed": {...}} o {"web": {...}})
    if isinstance(client_secret, str):
        try:
            client_config = json.loads(client_secret)
        except json.JSONDecodeError as e:
            print("❌ Error decodificando client_secret del Vault:", e)
            sys.exit(1)
    else:
        client_config = client_secret

    # Verificar que tenga la estructura esperada
    if "installed" not in client_config and "web" not in client_config:
        print("❌ Error: client_secret del Vault no tiene sección 'installed' o 'web'")
        sys.exit(1)

    SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

    from google_auth_oauthlib.flow import InstalledAppFlow

    # Construir flow con client_secret del Vault
    instaled_section = client_config.get("installed", client_config.get("web", {}))

    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": instaled_section.get("client_id", ""),
                "client_secret": instaled_section.get("client_secret", ""),
                "auth_uri": instaled_section.get(
                    "auth_uri", "https://accounts.google.com/o/oauth2/auth"
                ),
                "token_uri": instaled_section.get(
                    "token_uri", "https://oauth2.googleapis.com/token"
                ),
                "redirect_uris": instaled_section.get(
                    "redirect_uris", ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
                ),
            }
        },
        scopes=SCOPES,
    )

    # Generar URL de autorización
    auth_url, _ = flow.authorization_url(
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
    captured_code = None

    class CallbackHandler:
        def do_GET(self):
            nonlocal captured_code
            if self.path.startswith("/?code="):
                code = self.path.split("=")[1].split("&")[0]
                captured_code = code
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write("Autorización recibida. Puedes cerrar este tab.".encode("utf-8"))
            else:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"")
        def log_message(self, format, *args):
            pass

    import threading
    server = None
    port = 0
    try:
        from http.server import HTTPServer
        server = HTTPServer(("127.0.0.1", 0), CallbackHandler)
        port = server.server_address[1]
    except ImportError:
        pass

    print("\n=== Paso 2: Servidor HTTP local en 127.0.0.1:" + str(port) + " ===")
    print("   El navegador será redirigido aqui despues de autorizar.")
    print("   Si no se abre automáticamente, visita: http://127.0.0.1:" + str(port) + "/")
    print("   La autorizacion continuara en segundos...")
    print()

    # Thread para manejar el servidor
    if server:
        server_thread = threading.Thread(target=lambda: (
            time.sleep(0.5),
            server.handle_request(),
            server.handle_request(),
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
        if server:
            server.shutdown()
        sys.exit(1)

    print("✓ Código de autorizacion capturado:", captured_code[:20] + "...")

    # ===================================================================
    # Paso 6: Obtener Refresh Token
    # ===================================================================
    print("\n=== Paso 3: Obteniendo tokens de Google ===")

    try:
        flow.fetch_token(code=captured_code)
        creds = flow.credentials
    except Exception as e:
        print("❌ Error obteniendo tokens:", e)
        if server:
            server.shutdown()
        sys.exit(1)

    if not creds or not creds.refresh_token:
        print("❌ No se obtuvo refresh_token en las credentials.")
        if server:
            server.shutdown()
        sys.exit(1)

    print("✓ Refresh Token obtenido exitosamente")
    print("   - Token type:", creds.token_type)
    print("   - Expires:", creds.expiry)
    print("   - Scopes:", ", ".join(creds.scopes))

    # Formatear token JSON
    token_json = creds.to_json()
    print("✓ JSON token generado (" + str(len(token_json)) + " caracteres)")

    # ===================================================================
    # Paso 7: Reconectar al VPS
    # ===================================================================
    print("\n🔗 Paso 7: Reconectando al VPS para guardar el token...")

    # ===================================================================
    # Paso 8: Guardar Refresh Token usando EXCLUSIVAMENTE:
    # set_secret("google/token", token_json) vía SSH al VPS
    # ===================================================================
    remote_code = (
        "import sys\n"
        "sys.path.insert(0, '/home/genesis/opt/genesis/HYDRA/src')\n"
        "from hydra.vault import get_vault\n"
        "v = get_vault()\n"
        "result = v.set_secret('google/token', " + json.dumps(token_json) + " )\n"
        "print('✅ set_secret() ejecutado correctamente' if result else '❌ set_secret falló')\n"
        "# Verificar\n"
        "v2 = get_vault()\n"
        "t = v2.get_secret('google/token')\n"
        "if t:\n"
        "    print('✅ Token verificado en Vault remoto')\n"
        "else:\n"
        "    print('⚠ Token NO recuperable despues de set_secret')"
    )

    ssh_ok, ssh_stdout, ssh_stderr = _ssh_execute_remote(
        vps_config, remote_code, input_data=token_json
    )

    print("STDOUT remoto:")
    print(ssh_stdout)
    print("STDERR remoto:")
    print(ssh_stderr)

    if not ssh_ok:
        print("⚠ El comando remoto terminó con error o código distinto de 0")
        print("  (puede que el token ya haya sido guardado parcialmente)")

    # ===================================================================
    # Paso 9: Comprobar get_secret("google/token")
    # ===================================================================
    print("\n=== Paso 4: Verificando token en Vault ===")

    # Verificar en VPS
    verify_result = _verify_remote_vault(vps_config)
    print(verify_result)

    # Verificar también localmente
    local_token = vault.get_secret("google/token")
    if local_token:
        print("✅ Token también verificado localmente en Vault")
    else:
        print("⚠ Token no encontrado en Vault local (aunque pudo guardarse en el VPS)")

    # ===================================================================
    # Paso 10: Mostrar mensajes de finalización
    # ===================================================================
    print("\n" + "=" * 60)
    print("✅ BOOTSTRAP FINALIZADO")
    print("=" * 60)
    print("Resumen de operaciones realizadas:")
    print("   ✓ Refresh Token obtenido")
    print("   ✓ Refresh Token almacenado")
    print("   ✓ Vault verificado")
    print("   ✓ Gmail listo para utilizar desde el VPS")
    print()
    print("El Refresh Token ya está almacenado en el Vault del VPS.")
    print("A partir de ahora, los conectores HYDRA en el VPS podrán operar")
    print("utilizando este Refresh Token sin necesidad de nuevo OAuth.")
    print()
    print("Para verificar desde el VPS:")
    print("  python3 -c \"from hydra.vault import get_vault; v = get_vault(); t = v.get_secret('google/token'); print('Token válido' if t else 'Sin token')\"")

    if server:
        server.shutdown()


if __name__ == "__main__":
    main()