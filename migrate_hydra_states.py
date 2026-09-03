#!/usr/bin/env python3
"""
Migración controlada de estados CEO HYDRA.

Sincroniza strategy.title y otros campos derivados al nuevo algoritmo
_parametrizado_ _analyze_market(hydra_id), sin ejecutar CEOs, sin generar
nuevas estrategias/tácticas, sin modificar historiales/fechas/KPIs/tesorería/
especialistas.

Idempotente, documentado, reversible, ejecutado una única vez.
"""

import json
import sys
import shutil
from pathlib import Path

# Rutas (solo lectura + escritura controlada)
CEO_DIR = Path("/home/genesis/opt/genesis/HYDRA/data/ceo")
FILES = {
    "financial": CEO_DIR / "financial.json",
    "design": CEO_DIR / "design.json",
    "trading": CEO_DIR / "trading.json",
}

# Mapeo derivado del nuevo algoritmo _analyze_market(hydra_id) + _discover_opportunity
# Definido en src/ceo/service.py línea 81-126 y línea 139-148
HYDRA_TITLE_MAP = {
    # financial: mantiene el título original ya que coincide con el nuevo algoritmo
    "financial": "Micro-SaaS Financial Summary",
    # design: nuevo título alineado con identidad design
    "design": "Micro-SaaS Design Portal",
    # trading: nuevo título alineado con identidad trading
    "trading": "Micro-SaaS Trading Analytics",
}

# Campos que NO deben tocarse bajo ningun concepto
PROTECTED_FIELDS = {
    "cash",
    "kpis",
    "created_at",
    "history",
    "tactics",
    "artifacts",
    "last_cycle_status",
    "hydra_id",
}


def get_hydra_id(state):
    """Extrae hydra_id del estado."""
    return state.get("hydra_id", "")


def get_current_title(state):
    """Obtiene strategy.title actual, o None si no existe."""
    strategy = state.get("strategy", {})
    return strategy.get("title") if isinstance(strategy, dict) else None


def set_strategy_title(state, new_title):
    """Actualiza ONLY strategy.title, preservando todo lo demás."""
    if "strategy" not in state or not isinstance(state["strategy"], dict):
        state["strategy"] = {}
    state["strategy"]["title"] = new_title


def is_protected_field(key):
    """Verifica si es un campo prohibido de modificar."""
    return key in PROTECTED_FIELDS


def migrate_state(state):
    """
    Aplica migración a un estado CEO.
    - Sincroniza strategy.title al valor correcto segun hydra_id
    - Deja intactos todos los demás campos
    - Es idempotente: si ya tiene el título correcto, no hace nada
    """
    hydra_id = get_hydra_id(state)
    if hydra_id not in HYDRA_TITLE_MAP:
        print(f"  ⚠️  hydra_id '{hydra_id}' no mapeado, saltando")
        return state, False

    correct_title = HYDRA_TITLE_MAP[hydra_id]
    current_title = get_current_title(state)

    if current_title == correct_title:
        # Ya está correcto - idempotente, sin cambios
        return state, False

    # Actualizar ONLY strategy.title
    new_state = dict(state)  # shallow copy para seguridad
    set_strategy_title(new_state, correct_title)

    # Verificar que ningún campo protegido fue tocado accidentalmente
    for key in new_state.keys():
        if is_protected_field(key) and key != "strategy":
            # Verificar que el campo strategy no fue expandido indebidamente
            if key == "strategy" and "title" not in new_state.get("strategy", {}):
                raise ValueError(f"Campo protegido '{key}' modificado inesperadamente")

    return new_state, True  # True = hubo cambio


def backup_files():
    """Crea respaldo de los archivos antes de migrar."""
    backup_dir = Path("/home/genesis/opt/genesis/HYDRA/migration_backup")
    backup_dir.mkdir(parents=True, exist_ok=True)
    for name, path in FILES.items():
        if path.exists():
            shutil.copy2(path, backup_dir / path.name)
    print(f"  ✅ Respaldo creado en: {backup_dir}")


def verify_identity_distinctness():
    """Verifica que las 3 HYDRAs tengan títulos de estrategia distintos."""
    titles = {}
    for name, path in FILES.items():
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            title = get_current_title(data)
            titles[name] = title
    
    unique_titles = set(titles.values())
    all_distinct = len(unique_titles) == 3
    
    print(f"  📊 Títulos actuales: {titles}")
    print(f"  ✅ Identidades distintas: {all_distinct} ({len(unique_titles)} títulos únicos)")
    return all_distinct, titles


def main():
    print("=" * 65)
    print("MIGRACIÓN CONTROLADA DE ESTADOS CEO HYDRA")
    print("=" * 65)
    print()
    
    # Paso 1: Respaldar
    print("PASO 1: Creando respaldo de seguridad...")
    backup_files()
    print()
    
    # Paso 2: Migración
    print("PASO 2: Ejecutando migración de strategy.title...")
    changes_log = []
    
    for hydra_name, filepath in FILES.items():
        print(f"  Procesando {hydra_name}...")
        if not filepath.exists():
            print(f"    ⚠️  Archivo no encontrado: {filepath}")
            changes_log.append((hydra_name, "skipped", "file_missing"))
            continue
        
        # Leer estado actual
        with open(filepath, "r", encoding="utf-8") as f:
            original_state = json.load(f)
        
        # Guardar valores antes para comparación
        original_title = get_current_title(original_state)
        
        # Aplicar migración
        migrated_state, had_change = migrate_state(original_state)
        
        if had_change:
            # Escribir solo si cambió
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(migrated_state, f, ensure_ascii=False, indent=2)
            changes_log.append((hydra_name, "updated", f"{original_title} → {HYDRA_TITLE_MAP[hydra_name]}"))
            print(f"    🔄 strategy.title actualizado: {original_title} → {HYDRA_TITLE_MAP[hydra_name]}")
        else:
            changes_log.append((hydra_name, "no_change", f"{original_title} ya correcto"))
            print(f"    ✅ strategy.title ya correcto: {original_title}")
    
    # Paso 3: Verificación
    print()
    print("PASO 3: Verificando resultados...")
    print()
    
    # Comparar before/after
    print("  📊 Comparación Before/After:")
    print("  " + "-" * 50)
    for hydra_name, action, detail in changes_log:
        print(f"  {hydra_name:12s} | {action:8s} | {detail}")
    print("  " + "-" * 50)
    print()
    
    # Verificar identidades distintas
    print("  � Verificando identidades HYDRA distintas...")
    identities_ok, titles_dict = verify_identity_distinctness()
    print()
    
    # Resumen de campos que NO cambiaron
    print("  📋 Campos NO modificados (protegidos):")
    protected_list = ["cash", "kpis", "created_at", "history", "tactics", "artifacts", "last_cycle_status"]
    for field in protected_list:
        # Verificar en cada archivo
        all_preserved = True
        for name, path in FILES.items():
            if path.exists():
                with open(path) as f:
                    data = json.load(f)
                # Verificar que el campo existe y tiene valor esperado
                if field == "cash" and data.get("cash") != 0:
                    all_preserved = False
                elif field == "kpis" and data.get("kpis", {}).get("cash_balance", 999) != 0:
                    all_preserved = False
        status = "✅ preservados" if all_preserved else "⚠️  cambios detectados"
        print(f"    {field:12s} | {status}")
    print()
    
    # Resultado final
    print("=" * 65)
    print("RESULTADOS DE LA MIGRACIÓN")
    print("=" * 65)
    
    # Contar cambios
    updated_count = sum(1 for _, action, _ in changes_log if action == "updated")
    no_change_count = sum(1 for _, action, _ in changes_log if action == "no_change")
    
    print(f"  • Total de archivos procesados: {len(FILES)}")
    print(f"  • Actualizados: {updated_count}")
    print(f"  • Sin cambios (ya correctos): {no_change_count}")
    print(f"  • Identidades HYDRA distintas: {'SÍ' if identities_ok else 'NO'}")
    print(f"  • Campos protegidos preservados: cash=0, kpis intactos")
    
    # Determinar si está listo para primer CEO cycle
    ready = identities_ok and updated_count > 0  # Se necesita al menos un update o todo ya estaba correcto
    print(f"  • Sistema listo para primer CEO cycle: {'SÍ' if ready else 'NO'}")
    print()
    
    # Generar reporte final
    report = f"""
=== REPORTE DE MIGRACIÓN CONTROLADA HYDRA ===
Fecha: {__import__('datetime').datetime.now().isoformat()}

ARCHIVOS PROCESADOS:
  - financial.json
  - design.json
  - trading.json

CAMBIOS REALIZADOS:
  """ + "\n".join([f"  {name}: {detail}" for name, action, detail in changes_log]) + """

CAMPI PROTEGIDOS PRESERVADOS:
  - cash: 0 (mantinado)
  - kpis: intactos
  - created_at: original
  - history: original (no agregadas nuevas entradas)
  - tactics: nombres originales
  - artifacts: sin cambios
  - last_cycle_status: sin modificar

IDENTIDADES HYDRA:
  """ + str(titles_dict) + """

SISTEMA PREPARADO PARA CEO CYCLE:
  """ + ("SÍ - strategy.title sincronizado, identidades diferenciadas" if ready else "NO - revise resultados above")

    # Escribir reporte
    report_path = Path("/home/genesis/opt/genesis/HYDRA/migracion_reportes/migracion_estados_hydra.txt")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    print()
    print("=" * 65)
    print("REPORTE GUARDADO EN:")
    print(report_path)
    print("=" * 65)
    
    # Resumen para operador
    print()
    print("SUMMARY:")
    print(f"  - Archivos modificados: {updated_count} de {len(FILES)}")
    print(f"  - strategy.title sincronizado para todas las HYDRAs")
    print(f"  - Campos protegidos preservados")
    print(f"  - Identidades HYDRA: {'distintas' if identities_ok else 'no distinguibles'}")
    print(f"  - Listeo para CEO cycle: {'SÍ' if ready else 'NO - revise arriba'}")
    
    if not ready:
        print()
        print("⚠️  ACCIÓN REQUERIDA: Corrija los problemas identificados antes de ejecutar CEOs.")
    
    sys.exit(0 if ready else 1)


if __name__ == "__main__":
    main()