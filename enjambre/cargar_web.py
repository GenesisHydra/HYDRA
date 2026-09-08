import sqlite3
import urllib.request
import json

db_path = '/home/genesis/opt/genesis/HYDRA/enjambre/db/tareas.db'

print('[+] Solicitando plan de desarrollo a DeepSeek...')

prompt = '''
Eres DeepSeek, Director de HYDRA. Genera un JSON estricto con un lote de 4 tareas para la FASE 3: Desarrollo Web Genesis.
El formato debe ser exactamente una lista JSON como esta:
[
  {"modulo": "Web_Frontend", "descripcion": "Crear estructura base HTML5 semántica para la Landing Page de Genesis"},
  {"modulo": "Web_Styles", "descripcion": "Diseñar hojas de estilo CSS3 responsivas usando la paleta de colores de la marca HYDRA"},
  {"modulo": "Web_JS", "descripcion": "Implementar scripts en JS para animaciones e interactividad de la landing"},
  {"modulo": "Web_Assets", "descripcion": "Organizar carpeta de assets e integrar recursos de imagen de la marca"}
]
Responde UNICAMENTE con el JSON, sin texto explicativo.
'''

url = 'http://localhost:11434/api/generate'
payload = {'model': 'deepseek-coder-v2:16b', 'prompt': prompt, 'stream': False}
req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})

try:
    with urllib.request.urlopen(req) as resp:
        res_raw = json.loads(resp.read().decode())['response']
        start = res_raw.find('[')
        end = res_raw.rfind(']') + 1
        tareas = json.loads(res_raw[start:end])
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        for t in tareas:
            cursor.execute('INSERT INTO tareas (modulo, descripcion, agente) VALUES (?, ?, ?)',
                           (t['modulo'], t['descripcion'], 'qwen2.5-agent'))
        conn.commit()
        print(f'\n[+] ÉXITO: {len(tareas)} tareas de la Web Genesis registradas en tareas.db.')
        
        print('\n=== TAREAS EN COLA ===')
        cursor.execute('SELECT id, modulo, descripcion, estado FROM tareas WHERE estado = "PENDIENTE"')
        for r in cursor.fetchall():
            print(f'ID {r[0]} | {r[1]}: {r[2]} [{r[3]}]')
        conn.close()

except Exception as e:
    print(f'[-] Error registrando plan: {e}')
