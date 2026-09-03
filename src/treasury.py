# Treasury Controller - Capital Management

import json
import os
import uuid
from datetime import datetime

class TreasuryController:
    def __init__(self, treasury_file="data/treasury.json"):
        self.treasury_file = treasury_file
        self.data = self._load_treasury()
        
    def _load_treasury(self):
        if os.path.exists(self.treasury_file):
            with open(self.treasury_file, "r") as f:
                return json.load(f)
        return {
            "financial": {"capital": 0, "budget": 0, "expenses": 0, "revenue": 0, "profit": 0},
            "design": {"capital": 0, "budget": 0, "expenses": 0, "revenue": 0, "profit": 0},
            "trading": {"capital": 0, "budget": 0, "expenses": 0, "revenue": 0, "profit": 0},
            "system_reserves": 0
        }
    
    def _save_treasury(self):
        with open(self.treasury_file, "w") as f:
            json.dump(self.data, f, indent=2)
    
    def validate_profit(self, business_type: str, profit: float) -> bool:
        """Validar beneficio real >= 50 USD"""
        if profit >= 50:
            self._enable_reproduction(business_type, profit)
            return True
        return False
    
    def _enable_reproduction(self, business_type: str, profit: float):
        """Permitir creación de nueva HYDRA hija"""
        if business_type not in self.data:
            self.data[business_type] = {"capital": 0, "budget": 0, "expenses": 0, "revenue": 0, "profit": 0}
        
        # Transferir 25 USD a nueva hija
        transfer_amount = 25
        self.data[business_type]["capital"] += transfer_amount
        self.data["system_reserves"] -= transfer_amount
        
        self._save_treasury()
        print(f"  [TESORO] {business_type} transfirió {transfer_amount} USD a nueva HYDRA")
    
    def allocate_budget(self, business_type: str, amount: float) -> bool:
        """Asignar presupuesto solo si habrá revenue positivo"""
        if amount <= 0:
            return False
            
        max_budget = {
            "financial": 500,
            "design": 300,
            "trading": 300
        }
        
        if amount > max_budget.get(business_type, 500):
            print(f"  [TESORO] Presupuesto {amount} excede límite de {max_budget.get(business_type, 500)} para {business_type}")
            return False
            
        self.data[business_type]["budget"] += amount
        self.data["system_reserves"] -= amount
        self._save_treasury()
        return True
    
    def record_transaction(self, business_type: str, revenue: float, expenses: float = 0):
        """Registrar transacción financiera"""
        if business_type not in self.data:
            return
            
        self.data[business_type]["revenue"] += revenue
        self.data[business_type]["expenses"] += expenses
        self.data[business_type]["profit"] = self.data[business_type]["revenue"] - self.data[business_type]["expenses"]
        
        self._save_treasury()
    
    def get_status(self) -> dict:
        """Obtener estado completo del tesoro"""
        return self.data
    
    def add_system_reserve(self, amount: float):
        """Añadir reservas al sistema"""
        self.data["system_reserves"] += amount
        self._save_treasury()

# Singleton global treasury
treasury = TreasuryController()
