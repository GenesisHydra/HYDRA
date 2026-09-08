import os.path
import sys

print("=== VERIFICACIÓN DEL CONECTOR DE GMAIL ===")

cred_path = "/home/genesis/opt/genesis/HYDRA/proyectos/conectores/gmail/credentials.json"
token_path = "/home/genesis/opt/genesis/HYDRA/proyectos/conectores/gmail/token.json"

if not os.path.exists(cred_path):
    print(f"[-] FALTAN CREDENCIALES: No se encontró {cred_path}")
    print("[!] Por favor, coloca tu archivo 'credentials.json' descargado de Google Cloud Console en esa ruta.")
    sys.exit(1)

print("[+] Archivo 'credentials.json' detectado.")

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    print("[+] Librerías de Google detectadas correctamente.")
except ImportError:
    print("[-] FALTAN LIBRERÍAS: Instalando google-api-python-client google-auth-httplib2 google-auth-oauthlib...")
    os.system("pip3 install --quiet google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

if os.path.exists(token_path):
    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    print("[+] Token de acceso OAuth2 detectado y cargado.")
else:
    print("[!] No hay 'token.json'. Se requiere primera autenticación OAuth2.")
    creds = None

if creds and creds.valid:
    try:
        service = build('gmail', 'v1', credentials=creds)
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        print(f"[SUCCESS] Conexión exitosa con Gmail. Total de etiquetas leídas: {len(labels)}")
    except Exception as e:
        print(f"[-] Error al consultar la API de Gmail: {e}")
else:
    print("[!] Las credenciales requieren autenticación inicial.")
