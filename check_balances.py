import os
import json
import urllib.request

vault_file = "vault/crypto_wallets_production.json"

if not os.path.exists(vault_file):
    print("[ERROR] No se encuentra el archivo de carteras de producción.")
    exit(1)

with open(vault_file, "r") as f:
    wallets = json.load(f)

# Nodo RPC público de Polygon y contrato oficial de USDT en Polygon
RPC_URL = "https://polygon-rpc.com"
USDT_CONTRACT = "0xc2132D05D31c914a87C6611C10748AEb04B58e8F" # USDT en Polygon

def call_rpc(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        return {"error": str(e)}

print("--- AUDITORÍA DE SALDOS USDT (RED POLYGON) ---")

for hydra, info in wallets.items():
    address = info["public_address"]
    # Formatear la llamada ERC20 balanceOf(address) -> abi signature 0x70a08231
    clean_address = address[2:].lower().zfill(64)
    data_payload = "0x70a08231" + clean_address
    
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_call",
        "params": [
            {"to": USDT_CONTRACT, "data": data_payload},
            "latest"
        ],
        "id": 1
    }
    
    res = call_rpc(RPC_URL, payload)
    balance = 0.0
    if "result" in res and res["result"] and res["result"] != "0x":
        # USDT en Polygon tiene 6 decimales
        raw_val = int(res["result"], 16)
        balance = raw_val / 10**6
        
    print(f" -> {hydra.upper()} ({address}): {balance:.2f} USDT")

