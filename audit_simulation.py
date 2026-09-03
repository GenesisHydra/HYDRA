#!/usr/bin/env python3
"""Simulación de market_analysis por HYDRA con la nueva función parametrizada."""

def _analyze_market(hydra_id):
    hydra_profiles = {
        'financial': {
            'trend': 'growing demand for automated financial reporting',
            'size_eur': 200_000_000,
            'competitors': ['CompanyA', 'CompanyB']
        },
        'design': {
            'trend': 'growing demand for automated design and branding solutions',
            'size_eur': 150_000_000,
            'competitors': ['DesignCo', 'BrandCorp']
        },
        'trading': {
            'trend': 'growing demand for automated trading analytics and market insights',
            'size_eur': 180_000_000,
            'competitors': ['TradeAlpha', 'QuantStreet']
        }
    }
    profile = hydra_profiles.get(hydra_id, hydra_profiles['financial'])
    return {
        'trend': profile['trend'],
        'size_eur': profile['size_eur'],
        'competitors': profile['competitors']
    }

# Test each HYDRA
financial_market = _analyze_market('financial')
design_market = _analyze_market('design')
trading_market = _analyze_market('trading')

results = {
    'financial': financial_market,
    'design': design_market,
    'trading': trading_market
}

# Verify differences
trends_diff = (financial_market['trend'] != design_market['trend'] and 
               design_market['trend'] != trading_market['trend'] and 
               financial_market['trend'] != trading_market['trend'])
sizes_diff = (financial_market['size_eur'] != design_market['size_eur'] and 
              design_market['size_eur'] != trading_market['size_eur'] and 
              financial_market['size_eur'] != trading_market['size_eur'])
comps_diff = (set(financial_market['competitors']) != set(design_market['competitors']) and 
              set(design_market['competitors']) != set(trading_market['competitors']) and 
              set(financial_market['competitors']) != set(trading_market['competitors']))

with open('/home/genesis/opt/genesis/HYDRA/simulation_results.txt', 'w') as f:
    f.write("=== SIMULACIÓN: market_analysis por HYDRA ===\n\n")
    f.write("Financial HYDRA:\n")
    f.write(f"  trend: {financial_market['trend']}\n")
    f.write(f"  size_eur: {financial_market['size_eur']}\n")
    f.write(f"  competitors: {financial_market['competitors']}\n\n")
    f.write("Design HYDRA:\n")
    f.write(f"  trend: {design_market['trend']}\n")
    f.write(f"  size_eur: {design_market['size_eur']}\n")
    f.write(f"  competitors: {design_market['competitors']}\n\n")
    f.write("Trading HYDRA:\n")
    f.write(f"  trend: {trading_market['trend']}\n")
    f.write(f"  size_eur: {trading_market['size_eur']}\n")
    f.write(f"  competitors: {trading_market['competitors']}\n\n")
    f.write("=== RESULTADOS ===\n")
    f.write(f"Trends different: {trends_diff}\n")
    f.write(f"Sizes different: {sizes_diff}\n")
    f.write(f"Competitors different: {comps_diff}\n")
    f.write("\n")
    if trends_diff and sizes_diff and comps_diff:
        f.write("ÉXITO: Las tres HYDRAs ahora tienen market_analysis distintos\n")
    else:
        f.write("FALLO: Las market_analysis no son suficientemente distintas\n")