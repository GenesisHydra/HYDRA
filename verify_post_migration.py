#!/usr/bin/env python3
"""
Verificación final de consistencia POST-MIGRACIÓN.

Comprueba que el sistema está preparado para ejecutar el primer ciclo CEO
sin inconsistencias entre código corregido y estado persistente.
"""

import json
import sys
from pathlib import Path

CEO_DIR = Path("/home/genesis/opt/genesis/HYDRA/data/ceo")
FILES = {
    "financial": CEO_DIR / "financial.json",
    "design": CEO_DIR / "design.json",
    "trading": CEO_DIR / "trading.json",
}

HYDRA_TITLE_MAP = {
    "financial": "Micro-SaaS Financial Summary",
    "design": "Micro-SaaS Design Portal",
    "trading": "Micro-SaaS Trading Analytics",
}


def check_file(path, name):
    """Verifica un archivo JSON y devuelve su estado de consistencia."""
    if not path.exists():
        return f"❌ {name}: archivo no encontrado"
    
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    hydra_id = data.get("hydra_id", "unknown")
    strategy = data.get("strategy", {})
    title = strategy.get("title", "N/A")
    cash = data.get("cash", "N/A")
    kpis = data.get("kpis", {})
    
    # Verificar consistencia
    expected_title = HYDRA_TITLE_MAP.get(hydra_id, "Desconocido")
    title_ok = title == expected_title
    cash_ok = cash == 0
    kpis_ok = isinstance(kpis, dict)  # kpis debe ser diccionario
    
    issues = []
    if not title_ok:
        issues.append(f"  title esperada: '{expected_title}', got: '{title}'")
    if not cash_ok:
        issues.append(f"  cash esperado: 0, got: {cash}")
    if not kpis_ok:
        issues.append(f"  kpis no es diccionario: {kpis}")
    
    status = "✅" if not issues else "❌"
    result = f"{status} {name}: title={title}, cash={cash}, kpis_dict={isinstance(kpis, dict)}"
    if issues:
        result += " [" + "; ".join(issues) + "]"
    
    return result


def main():
    print("=" * 65)
    print("VERIFICACIÓN FINAL POST-MIGRACIÓN")
    print("=" * 65)
    print()
    
    all_ok = True
    for hydra_name, path in FILES.items():
        result = check_file(path, hydra_name.capitalize())
        print(result)
        # Extraer ok status de forma simple
        if "❌" in result:
            all_ok = False
    
    print()
    print("=" * 65)
    print("RESUMEN EJECUTIVO")
    print("=" * 65)
    print()
    
    # Verificar identidades distintas
    titles = {}
    for name, path in FILES.items():
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            hydra_id = data.get("hydra_id", "unknown")
            title = data.get("strategy", {}).get("title", "N/A")
            titles[hydra_id] = title
    
    unique_titles = set(titles.values())
    identities_distinct = len(unique_titles) == 3
    
    print(f"• Total de archivos CEO verificados: {len(FILES)}")
    print(f"• strategy.title coherente con identidad HYDRA: {'SÍ' if all_ok else 'PARCIAL'}")
    print(f"• cash: 0 en todas las HYDRAs: {'SÍ' if all_ok else 'NO'}")
    print(f"• kpis son diccionarios: {'SÍ' if all_ok else 'NO'}")
    print(f"• Identidades HYDRA distintas (3 títulos únicos): {'SÍ' if identities_distinct else 'NO'}")
    print(f"• Sistema listo para primer CEO cycle: {'SÍ' if (all_ok and identities_distinct) else 'NO'}")
    print()
    
    if all_ok and identities_distinct:
        print("✅ AUTORIZACIÓN CONCEDIDA: Ejecutar primer ciclo CEO")
    else:
        print("❌ PROBLEMAS DETECTADOS: Revisar resultados arriba")
    
    print()
    print("Ruta reporte detallado:")
    print("  /home/genesis/opt/genesis/HYDRA/migracion_reportes/migracion_estados_hydra.txt")
    
    return 0 if (all_ok and identities_distinct) else 1


if __name__ == "__main__":
    sys.exit(main())