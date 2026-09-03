#!/usr/bin/env python3
"""Validación del primer ciclo CEO - modo solo lectura y reporte."""

import json
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


def check_hydra(path, name):
    """Verifica el estado de una HYDRA después del CEO cycle."""
    with open(path) as f:
        data = json.load(f)
    
    title = data.get("strategy", {}).get("title", "N/A")
    cash = data.get("cash", 0)
    kpis = data.get("kpis", {})
    status = data.get("last_cycle_status", "N/A")
    artifacts = len(data.get("artifacts", []))
    history = len(data.get("history", []))
    
    expected_title = HYDRA_TITLE_MAP.get(name, "Desconocido")
    title_ok = title == expected_title
    cash_ok = cash == 0
    kpis_ok = isinstance(kpis, dict)
    
    issues = []
    if not title_ok:
        issues.append(f"title esperada='{expected_title}', got='{title}'")
    if not cash_ok:
        issues.append(f"cash esperado=0, got={cash}")
    if not kpis_ok:
        issues.append(f"kpis no es diccionario")
    
    status_mark = "✅" if not issues else "❌"
    return {
        "name": name,
        "title": title,
        "expected_title": expected_title,
        "title_ok": title_ok,
        "cash": cash,
        "cash_ok": cash_ok,
        "kpis_ok": kpis_ok,
        "status": status,
        "artifacts": artifacts,
        "history": history,
        "issues": issues,
        "status_mark": status_mark
    }


def main():
    print("=" * 70)
    print("VALIDACIÓN DEL PRIMER CICLO CEO - RESULTADOS OFICIALES")
    print("=" * 70)
    print()
    
    results = {}
    for hydra_name, path in FILES.items():
        result = check_hydra(path, hydra_name)
        results[hydra_name] = result
        print(f"{result['status_mark']} {result['name']:12s} | title={result['title']:30s} | "
              f"cash={result['cash']:3d} | status={result['status']:8s} | "
              f"artifacts={result['artifacts']:3d} | history={result['history']:3d}")
        if result['issues']:
            for issue in result['issues']:
                print(f"           ↳ PROBLEMA: {issue}")
    
    print()
    
    # Global validations
    print("=== VALIDACIONES GLOBALES ===")
    
    # 1. Sin convergencia
    titles = {h: r['title'] for h, r in results.items()}
    unique_titles = set(titles.values())
    no_convergence = len(unique_titles) != 1  # False if all same (converged)
    print(f"1. Sin convergencia hacia modelo unico: {'SÍ' if no_convergence else 'NO'} ")
    print(f"   Titulos unicos: {len(unique_titles)} ({titles})")
    
    # 2. Identidades diferenciadas
    identities_distinct = len(unique_titles) == 3
    print(f"2. Identidades HYDRA diferenciadas: {'SÍ' if identities_distinct else 'NO'} ")
    
    # 3. Tesorería coherente
    all_cash_zero = all(r['cash_ok'] for r in results.values())
    print(f"3. Tesoreraria coherente (cash=0): {'SÍ' if all_cash_zero else 'NO'} ")
    
    # 4. KPIs intactos
    all_kpis_dict = all(r['kpis_ok'] for r in results.values())
    print(f"4. KPIs intactos (diccionarios): {'SÍ' if all_kpis_dict else 'NO'} ")
    
    # 5. Status SUCCESS
    all_success = all(r['status'] == 'SUCCESS' for r in results.values())
    print(f"5. Todos los CEOs con status SUCCESS: {'SÍ' if all_success else 'NO'} ")
    
    # 6. No referencias al modelo unico
    no_old_model = all(r['title'] != "Micro-SaaS Financial Summary" or 
                       (r['name'] == 'financial' and r['title_ok']) 
                       for r in results.values() for name in [r['name']])
    # Simplified: check that only financial has the financial title
    financial_has_financial = results['financial']['title'] == "Micro-SaaS Financial Summary"
    design_has_portal = results['design']['title'] == "Micro-SaaS Design Portal"
    trading_has_analytics = results['trading']['title'] == "Micro-SaaS Trading Analytics"
    no_old_model_check = financial_has_financial and design_has_portal and trading_has_analytics
    print(f"6. No referencias modelo unico antiguo: {'SÍ' if no_old_model_check else 'NO'} ")
    print(f"   financial: Micro-SaaS Financial Summary = {financial_has_financial}")
    print(f"   design: Micro-SaaS Design Portal = {design_has_portal}")
    print(f"   trading: Micro-SaaS Trading Analytics = {trading_has_analytics}")
    
    print()
    print("=== AUTORIZACIÓN ===")
    all_pass = (no_convergence and identities_distinct and all_cash_zero and 
                all_kpis_dict and all_success and no_old_model_check)
    
    if all_pass:
        print("✅ AUTORIZACIÓN CONCEDIDA: Primer ciclo CEO validado exitosamente")
        print("   - Sistema listo para continuar (según política de segundos ciclos)")
    else:
        print("❌ PROBLEMAS DETECTADOS: Revisar resultados arriba")
    
    print()
    print("Ruta reporte detallado:")
    print("  /home/genesis/opt/genesis/HYDRA/ceo_validation_report.txt")
    
    return 0 if all_pass else 1


if __name__ == "__main__":
    main()