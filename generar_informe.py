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

url = "http://127.0.0.1:4000/v1/chat/completions"
headers = {"Content-Type": "application/json"}
payload = {
    "model": "deepseek-coder-v2:16b",
    "messages": [{"role": "user", "content": prompt}]
}

try:
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
    with urllib.request.urlopen(req) as response:
        res = json.loads(response.read().decode('utf-8'))
        contenido = res['choices'][0]['message']['content']
        
        # Guardar en la carpeta de auditorías
        ruta = '/home/genesis/opt/genesis/HYDRA/docs/auditorias/informe_ceos_hydra.txt'
        with open(ruta, 'w', encoding='utf-8') as f:
            f.write(contenido)
            
        print("\n=== INFORME GENERADO CON ÉXITO Y GUARDADO EN EN EL REPOSITORIO ===\n")
        print(contenido)
except Exception as e:
    print(f"Error al conectar con DeepSeek / LiteLLM: {e}")
