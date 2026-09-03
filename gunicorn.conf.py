# Configuración gunicorn para GitHub Pages
import os

# Number of worker processes
workers = int(os.environ.get("WORKERS", "4"))

# Bind to 0.0.0.0:8000 (GitHub Pages uses this port)
bind = "0.0.0.0:8000"

# Time out
timeout = 120

# Log level
loglevel = "info"

# Access log
accesslog = "-"

# Error log
errorlog = "-"
