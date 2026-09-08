import sqlite3
import requests
import time
import traceback
import json
import os

DB_PATH = "/home/genesis/opt/genesis/HYDRA/enjambre/db/tareas.db"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_EXEC = "qwen2.5-agent:latest"
MODEL_DIRECTOR = "deepseek-coder-v2:latest"
MAX_RETRIES = 3
TIMEOUT_SECONDS = 180
DOCUMENTO_MADRE = "/home/genesis/opt/genesis/HYDRA/docs/memoria/3_larga_distancia/DOCUMENTO_MADRE_HYDRA.md"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    return conn

def despertar_director():
    print("[*] Cola de tareas vacía. Despertando a DeepSeek (Director) para consultar el Roadmap y crear nuevas tareas...")
    
    # Leer el documento madre para contexto
    contenido_madre = ""
    if os.path.exists(DOCUMENTO_MADRE):
        with open(DOCUMENTO_MADRE, "r", encoding="utf-8") as f:
            contenido_madre = f.read()

    prompt = f"""Eres DeepSeek-coder-v2, Director de Operaciones del Ecosistema Hydra (Grupo Génesis).
Analiza el siguiente DOCUMENTO MADRE y el Roadmap de Expansión. La cola de tareas actual está vacía.
Tu objetivo es determinar cuál es el siguiente paso exacto que debemos dar y generar una nueva tarea clara para las hormiguitas obreras (en formato de texto breve que se pueda insertar en la base de datos).

DOCUMENTO MADRE:
{contenido_madre}

Responde unicamente con la descripcion de la siguiente tarea pendiente que se debe inyectar en la base de datos para avanzar en el roadmap.""""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": MODEL_DIRECTOR, "prompt": prompt, "stream": False},
            timeout=120
        )
        if response.status_code == 200:
            res_json = response.json()
            nueva_tarea = res_json.get("response", "").strip()
            if nueva_tarea:
                print(f"[+] DeepSeek ha generado la nueva tarea: {nueva_tarea}")
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO tareas (modulo, descripcion, estado, reintentos) VALUES (?, ?, ?, ?)",
                               ("enjambre", nueva_tarea, "PENDIENTE", 0))
                conn.commit()
                conn.close()
                return True
        print("[!] No se pudo obtener respuesta válida del Director.")
    except Exception as e:
        print(f"[!] Error al conectar con DeepSeek: {e}")
    return False

def process_task():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("BEGIN IMMEDIATE")
    cursor.execute("""
        SELECT id, modulo, descripcion, reintentos
        FROM tareas
        WHERE estado = PENDIENTE
        ORDER BY id ASC LIMIT 1
    """)
    task = cursor.fetchone()

    if not task:
        conn.rollback()
        conn.close()
        # Si no hay tareas, despertamos al director
        despertar_director()
        return False

    task_id, modulo, descripcion, reintentos = task["id"], task["modulo"], task["descripcion"], task["reintentos"]
    
    cursor.execute("UPDATE tareas SET estado = EN_PROCESO WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

    print(f"[*] Ejecutando tarea #{task_id} [{modulo}]: {descripcion}")
    
    # Llamada a la hormiguita obrera (qwen2.5-agent)
    prompt = f"Actúa como hormiguita obrera de ingeniería. Realiza o simula la ejecución de esta tarea corporativa: {descripcion}"
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": MODEL_EXEC, "prompt": prompt, "stream": False},
            timeout=TIMEOUT_SECONDS
        )
        if response.status_code == 200:
            resultado = response.json().get("response", "Completado sin texto")
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE tareas SET estado = COMPLETADA WHERE id = ?", (task_id,))
            conn.commit()
            conn.close()
            print(f"[OK] Tarea #{task_id} completada con éxito.")
            return True
        else:
            raise Exception(f"HTTP error {response.status_code}")
    except Exception as e:
        print(f"[!] Error en tarea #{task_id}: {e}")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE tareas SET estado = FALLIDA, reintentos = reintentos + 1 WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        return False

if __name__ == "__main__":
    print("[*] Iniciando motor autónomo de Hydra con ciclo de Director activo...")
    while True:
        success = process_task()
        if not success:
            print("[*] Esperando ciclo o reposo antes de reintentar...")
            time.sleep(10)
