import os
import json
import secrets

vault_dir = "vault"
os.makedirs(vault_dir, exist_ok=True)
wallets_file = os.path.join(vault_dir, "crypto_wallets_production.json")

if os.path.exists(wallets_file):
    print("[INFO] Las carteras corporativas ya están fijadas y registradas.")
    with open(wallets_file, "r") as f:
        data = json.load(f)
    for h, info in data.items():
        print(f" -> {h.upper()}: {info['public_address']}")
else:
    from eth_account import Account
    Account.enable_unaudited_hdwallet_features()
    production_wallets = {}
    for hydra in ["hydra_1_sales", "hydra_2_conversion", "hydra_3_revenue"]:
        account = Account.create(secrets.token_hex(32))
        production_wallets[hydra] = {
            "network": "EVM (Polygon / BSC / Ethereum / Arbitrum)",
            "asset": "USDT / USDC",
            "public_address": account.address,
            "private_key": account.key.hex(),
            "status": "Production_Active_Permanent"
        }
    with open(wallets_file, "w") as f:
        json.dump(production_wallets, f, indent=4)
    os.chmod(wallets_file, 0o600)
    print("[ÉXITO] Carteras permanentes creadas y bloqueadas.")
    for h, data in production_wallets.items():
        print(f" -> {h.upper()}: {data['public_address']}")
