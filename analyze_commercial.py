#!/usr/bin/env python3
"""
ANALYSIS: Why commercial research orders weren't executed
Classifying limitations and proposing autonomy roadmap v2
"""

import json
import os

results = {}

# 1. CEO STATES - BUSINESS STATUS
print("=== CEO STATES ===")
for hydra in ['financial', 'design', 'trading']:
    path = f'/home/genesis/opt/genesis/HYDRA/data/ceo/{hydra}.json'
    try:
        with open(path) as f:
            data = json.load(f)
        results[hydra] = {
            'title': data.get('strategy', {}).get('title', 'N/A'),
            'cash': data.get('cash', 0),
            'status': data.get('last_cycle_status', 'N/A'),
            'artifacts': len(data.get('artifacts', [])),
            'history_len': len(data.get('history', []))
        }
        print(f"{hydra.upper}: title={results[hydra]['title']}, cash={results[hydra]['cash']}, status={results[hydra]['status']}, artifacts={results[hydra]['artifacts']}, history={results[hydra]['history_len']}")
    except Exception as e:
        results[hydra] = {'error': str(e)}
        print(f"{hydra.upper}: ERROR - {e}")

results['summary_business'] = {
    'financial': results['financial'],
    'design': results['design'],
    'trading': results['trading'],
    'overall': '0 commercial progress across all 3 HYDRAs'
}

# 2. TREASURY
print("\n=== TREASURY ===")
with open('/home/genesis/opt/genesis/HYDRA/data/treasury.json') as f:
    treasury = json.load(f)
results['treasury'] = treasury
print(f"treasury: {treasury}")

# 3. ASSIGNMENTS
print("\n=== ASSIGNMENTS ===")
with open('/home/genesis/opt/genesis/HYDRA/data/team/assignments.json') as f:
    assignments_data = json.load(f)
hydra_assignments = {}
for a in assignments_data.get('assignments', []):
    hid = a.get('hydra_id', 'unknown')
    if hid not in hydra_assignments:
        hydra_assignments[hid] = []
    hydra_assignments[hid].append(f"{a['specialist_domain']}/{a['role']}")
for hydra in ['financial', 'design', 'trading']:
    results[f'{hydra}_assignments'] = hydra_assignments.get(hydra, [])
    print(f"{hydra.upper}: {results[f'{hydra}_assignments']}")

# 4. ARTIFACTS
print("\n=== ARTIFACTS ===")
for hydra in ['financial', 'design', 'trading']:
    path = f'/home/genesis/opt/genesis/HYDRA/data/assets/{hydra}'
    try:
        files = len([f for f in os.listdir(path) 
                     if f.endswith(('.py', '.md', '.csv'))])
        results[f'{hydra}_artifact_count'] = files
        print(f"{hydra.upper}: {files} artifacts")
    except:
        results[f'{hydra}_artifact_count'] = 'N/A'

# 5. SUMMARY
print("\n=== SUMMARY ===")
print("3 HYDRAs with 0 commercial progress")
print("0 clients, 0 sales, 0 revenues")
print("54 artifacts generated (18 per HYDRA) - all technical")
print(f"Cash: 0 in all HYDRAs (post-audit correction)")
print(f"Treasury: {treasury}")

results['summary'] = {
    'commercial_progress': '0/3 HYDRAs advanced',
    'artifacts': '54 technical, 0 commercial',
    'cash': '0 in all HYDRAs',
    'treasury': treasury
}

# Save results
output_path = Path('/home/genesis/opt/genesis/HYDRA/analysis_commercial_research.json')
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\nResults saved to: {output_path}")
print(f"Full path: {output_path}")