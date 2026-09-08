import sqlite3
import urllib.request
import json

def consultar_ollama(model, system_prompt, prompt):
    url = "http://localhost:11434/api/generate"
    data = {
        "model": model,
        "system": system_prompt,
        "prompt": prompt,
        "stream": False
    }
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode('utf-8'))
            return res.get("response", "")
    except Exception as e:
        return f"Error al conectar con Ollama: {e}"

SYSTEM_DIRECTOR = """Eres el Director de Operaciones de HYDRA. Tu función es dirigir al enjambre de IAs, tomar decisiones técnicas avanzadas, gestionar el Roadmap en el Documento Madre y hacer cumplir la expansión corporativa a $0 coste."""

SYSTEM_OBRERA = """Eres la Hormiguita Obrera de HYDRA. Tu función es ejecutar tareas de alta frecuencia, filtrar datos, hacer scraping y procesar mensajes velozmente."""

print("=== PROBANDO CONEXIÓN RESTRUCTURADA DEL ENJAMBRE ===")
print("1. Probando Obrera (qwen2.5-agent:latest)...")
res_qwen = consultar_ollama("qwen2.5-agent:latest", SYSTEM_OBRERA, "Confirma en 5 palabras que estás lista para tus tareas.")
print(f"Respuesta Obrera: {res_qwen.strip()}")

print("\n2. Probando Director (deepseek-coder-v2:16b)...")
res_deepseek = consultar_ollama("deepseek-coder-v2:16b", SYSTEM_DIRECTOR, "Confirma en 5 palabras tu rol como Director de HYDRA.")
print(f"Respuesta Director: {res_deepseek.strip()}")
