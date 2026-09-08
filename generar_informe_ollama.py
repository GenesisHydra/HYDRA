import urllib.request
import json

prompt = """
Actúa como Auditor Ejecutivo de Negocio de la corporación HYDRA.
Analiza la estructura global, subcarpetas (trading, design, financial, projects, proyectos), conectores y gobernanza del sistema.

Genera un informe gerencial exhaustivo sobre los CEOs y Agentes Especialistas de las tres unidades (TRADING, DESIGN, FINANCIAL).
Debes responder concretamente a los siguientes 5 puntos para cada unidad:

1. ¿Qué han creado hasta ahora (activos, productos, sistemas)?
2. ¿Qué han vendido, facturado o comercializado realmente?
3. ¿Qué competencia han estudiado o qué análisis de mercado han realizado?
4. ¿Qué van a hacer a continuación (plan de acción inmediato y roadmap)?
5. ¿Por qué están paradas o bloqueadas actualmente y cuál es la solución estratégica exacta para desbloquearlas?
"""

url = "http://127.0.0.1:11434/api/generate"
payload = {
    "model": "deepseek-coder-v2:16b",
    "prompt": prompt,
    "stream": False
}

try:
    print("Enviando consulta a Ollama (deepseek-coder-v2:16b)... Por favor espera.")
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as response:
        res = json.loads(response.read().decode('utf-8'))
        contenido = res.get('response', '')
        
        ruta = '/home/genesis/opt/genesis/HYDRA/docs/auditorias/informe_ceos_hydra.txt'
        with open(ruta, 'w', encoding='utf-8') as f:
            f.write(contenido)
            
        print("\n=== INFORME GENERADO Y GUARDADO EN EL REPOSITORIO ===\n")
        print(contenido)
except Exception as e:
    print(f"Error al conectar con Ollama: {e}")
