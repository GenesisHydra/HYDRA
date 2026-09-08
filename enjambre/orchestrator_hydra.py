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
TIMEOUT_SECONDS = 300
SKILLS_DIR = "/home/genesis/opt/genesis/HYDRA/enjambre/skills"

def load_skill(skill_filename):
    path = os.path.join(SKILLS_DIR, skill_filename)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""
    return ""

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    return conn

def unload_model(model_name):
    try:
        requests.post(OLLAMA_URL, json={"model": model_name, "keep_alive": 0}, timeout=10)
    except Exception:
        pass

def run_ollama(model, prompt):
    payload = {"model": model, "prompt": prompt, "stream": False}
    response = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json().get("response", "")

def process_qwen_tasks():
    processed_any = False
    while True:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("SELECT id, modulo, descripcion, reintentos FROM tareas WHERE estado = 'PENDIENTE' ORDER BY id ASC LIMIT 1")
        task = cursor.fetchone()

        if not task:
            conn.rollback()
            conn.close()
            break

        task_id, modulo, descripcion, reintentos = task["id"], task["modulo"], task["descripcion"], task["reintentos"]
        cursor.execute("UPDATE tareas SET estado = 'EN_PROCESO' WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()

        processed_any = True
        print(f"[QWEN EXEC] Procesando Tarea ID {task_id} [{modulo}]...")

        skill_context = ""
        if any(k in modulo.lower() for k in ["web", "front", "style", "css", "html", "ui", "js", "design"]):
            skill_context = load_skill("web_design.md")
            if skill_context:
                print(f"[SKILL INJECTED] Aplicando Skill de Diseno a Tarea ID {task_id}")

        if skill_context:
            prompt = skill_context + "\n\n---\nTAREA TECNICA:\nModulo: " + str(modulo) + "\nInstrucciones: " + str(descripcion) + "\n\nGenera codigo funcional, limpio y de alta calidad estetica."
        else:
            prompt = "Modulo: " + str(modulo) + "\nInstrucciones: " + str(descripcion) + "\nGenera codigo funcional e instrucciones precisas."

        try:
            output = run_ollama(MODEL_EXEC, prompt)
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE tareas SET estado = 'COMPLETADA', resultado = ?, log_error = NULL WHERE id = ?", (output, task_id))
            conn.commit()
            conn.close()
            print(f"[QWEN EXEC] Tarea ID {task_id} COMPLETADA.")
        except Exception as e:
            err_msg = traceback.format_exc()
            print(f"[ERROR QWEN] Fallo en Tarea ID {task_id}: {e}")
            conn = get_db_connection()
            cursor = conn.cursor()
            new_state = "PENDIENTE" if reintentos + 1 < 3 else "ERROR"
            cursor.execute("UPDATE tareas SET estado = ?, reintentos = reintentos + 1, log_error = ? WHERE id = ?", (new_state, err_msg, task_id))
            conn.commit()
            conn.close()

    if processed_any:
        unload_model(MODEL_EXEC)
    return processed_any

def trigger_deepseek_planner():
    print("[DEEPSEEK STRATEGY] Invocando al Director para planificacion...")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, modulo, estado FROM tareas ORDER BY id DESC LIMIT 5")
        recent_tasks = cursor.fetchall()
        conn.close()

        summary = "\n".join([f"ID {t['id']} [{t['modulo']}]: {t['estado']}" for t in recent_tasks])
        prompt = "Eres el Arquitecto Director de HYDRA.\nResumen reciente:\n" + summary + "\n\nGenera la siguiente tarea tecnica prioritaria.\nResponde UNICAMENTE en formato JSON valido con claves modulo y descripcion."

        raw_output = run_ollama(MODEL_DIRECTOR, prompt)
        print("[DEEPSEEK STRATEGY] Plan generado exitosamente.")
        
        start = raw_output.find("{")
        end = raw_output.rfind("}") + 1
        if start != -1 and end != 0:
            json_str = raw_output[start:end]
            data = json.loads(json_str)
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO tareas (modulo, descripcion, agente, estado) VALUES (?, ?, ?, 'PENDIENTE')",
                           (data['modulo'], data['descripcion'], MODEL_EXEC))
            conn.commit()
            conn.close()
            print(f"[DEEPSEEK STRATEGY] Nueva tarea inyectada: {data['modulo']}")
    except Exception as e:
        print(f"[ERROR DEEPSEEK] No se pudo invocar la planificacion: {e}")
    finally:
        unload_model(MODEL_DIRECTOR)

if __name__ == "__main__":
    print("[ORQUESTADOR HYDRA] Iniciado con Soporte para Skills de Diseno.")
    while True:
        processed = process_qwen_tasks()
        if not processed:
            trigger_deepseek_planner()
            print("[ORQUESTADOR HYDRA] Esperando 60 segundos antes del siguiente ciclo...")
            time.sleep(60)
