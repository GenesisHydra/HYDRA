Resumen (máximo 10 líneas):
Se implementó el módulo HYDRA Mail para integrar Gmail API mediante OAuth 2.0 oficial.
Se eliminó la implementación duplicada y obsoleta (auth_gmail.py).
Se utiliza flujo de autorización con authorization_url y fetch_token, sin localhost.
Las credenciales se almacenan de forma segura en el Vault de HYDRA (token solo).
Se agregó el módulo src/hydra/mail/gmail_client.py con funciones de envío, lectura, etiquetas y búsqueda.
Se actualizó requirements.txt con las dependencias necesarias de Google API.
Se creó __init__.py para el paquete mail.
Se guardó el resumen en SUMMARY.md.
Archivos modificados:
- src/hydra/mail/gmail_client.py (reescrito)
- src/hydra/mail/auth_gmail.py (eliminado)
- src/hydra/mail/__init__.py (creado)
- SUMMARY.md (creado/actualizado)
Rutas exactas:
- /home/genesis/opt/genesis/HYDRA/src/hydra/mail/gmail_client.py
- /home/genesis/opt/genesis/HYDRA/src/hydra/mail/auth_gmail.py (eliminado)
- /home/genesis/opt/genesis/HYDRA/src/hydra/mail/__init__.py
- /home/genesis/opt/genesis/HYDRA/SUMMARY.md
Commits realizados:
- gh-pages: cd1c2e1 Implement Gmail API OAuth2 flow usando authorization_url + fetch_token, eliminar auth_gmail.py duplicado, añadir módulo HYDRA Mail con Vault
Qué queda pendiente:
- Probar la integración manualmente ingresando el código de autorización cuando se solicite.
- Después de la autenticación, ejecutar pruebas de envío y lectura de correo.
¿Necesita intervención humana?:
Sí. Se requiere que el usuario visite la URL de autorización, conceda permisos y proporcione el código de autorización para completar el flujo OAuth y guardar el token en el Vault.
Evidencias reales obtenidas:
- El módulo gmail_client.py se compila sin errores y genera la URL de autorización correctamente.
- El vault ya contiene el client_secret (configurado previamente).
- El flujo elimina código duplicado y utiliza solo una instancia de InstalledAppFlow.
Resumen guardado en: /home/genesis/opt/genesis/HYDRA/SUMMARY.md
