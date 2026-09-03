# Treasury Controller - Capital Management with Database Persistence

import json
import os
from datetime import datetime
from typing import Optional, List

from database import SessionLocal, TreasuryStateModel, TreasuryHistoryModel

class TreasuryController:
    def __init__(self, session: Optional[SessionLocal] = None):
        self.session = session or SessionLocal()
        # Ensure treasury state rows exist for each business type
        self._ensure_initial_state()
    
    def _ensure_initial_state(self):
        """Ensure that treasury state rows exist for each business type."""
        business_types = ["financial", "design", "trading"]
        for btype in business_types:
            state = self.session.query(TreasuryStateModel).filter(TreasuryStateModel.business_type == btype).first()
            if not state:
                state = TreasuryStateModel(business_type=btype)
                self.session.add(state)
        self.session.commit()
    
    def _get_state(self, business_type: str) -> TreasuryStateModel:
        """Get treasury state for a business type."""
        state = self.session.query(TreasuryStateModel).filter(TreasuryStateModel.business_type == business_type).first()
        if not state:
            raise ValueError(f"Treasury state for business type {business_type} not found")
        return state
    
    def _add_history(self, history_type: str, **kwargs):
        """Add a history record."""
        history = TreasuryHistoryModel(
            type=history_type,
            timestamp=datetime.utcnow(),
            **kwargs
        )
        self.session.add(history)
        self.session.commit()
    
    def validate_profit(self, hydra_id: str, profit: float) -> bool:
        """Validar beneficio real >= 50 USD
        Permitir reproducción si cumple criterios
        """
        if profit >= 50:
            self.transfer_to_daughter(hydra_id, f"{hydra_id}_replica")
            self._add_history(
                "profit_validation",
                hydra_id=hydra_id,
                amount=profit,
                action="reproduction_enabled"
            )
            return True
        return False
        
    def allocate_budget(self, hydra_id: str, amount: float, reason: str) -> bool:
        """Asignar presupuesto con límites estrictos
        Aprobar solo gastos que generen revenue
        """
        if amount <= 0:
            return False
            
        max_budgets = {
            "financial": 500,
            "design": 300,
            "trading": 300
        }
        
        if hydra_id not in max_budgets:
            return False
            
        if amount > max_budgets[hydra_id]:
            self._add_history(
                "budget_allocation",
                hydra_id=hydra_id,
                amount=amount,
                reason=reason,
                action="rejected",
                message=f"Exceeds limit of {max_budgets[hydra_id]}"
            )
            return False
            
        # Update budget in treasury state
        state = self._get_state(hydra_id)
        state.budget += amount
        self.session.add(state)
        
        self._add_history(
            "budget_allocation",
            hydra_id=hydra_id,
            amount=amount,
            reason=reason,
            action="approved"
        )
        self.session.commit()
        return True
        
    def transfer_to_daughter(self, mother_id: str, daughter_id: str) -> bool:
        """Transferir 25 USD si HYDRA alcanza beneficio estable
        """
        # Get mother state
        mother_state = self._get_state(mother_id)
        if mother_state.profit < 25:
            return False
            
        transfer_amount = 25
        
        # Update mother state
        mother_state.profit -= transfer_amount
        mother_state.capital -= transfer_amount  # assuming capital also decreases
        
        # Get or create daughter state
        try:
            daughter_state = self._get_state(daughter_id)
        except ValueError:
            # If daughter_id is not a known business type, create a new state
            daughter_state = TreasuryStateModel(business_type=daughter_id, capital=0, budget=0, expenses=0, revenue=0, profit=0)
            self.session.add(daughter_state)
        
        # Update daughter state
        daughter_state.profit += transfer_amount
        daughter_state.capital += transfer_amount
        
        self.session.add(mother_state)
        self.session.add(daughter_state)
        
        self._add_history(
            "transfer",
            hydra_id=mother_id,
            amount=transfer_amount,
            action="completed"
        )
        self.session.commit()
        return True
        
    def auto_balance(self):
        """Generar balances económicos automáticos
        """
        states = self.session.query(TreasuryStateModel).all()
        for state in states:
            balance = state.profit
            if balance < 0:
                deficit = abs(balance)
                self._add_history(
                    "auto_balance",
                    hydra_id=state.business_type,
                    amount=deficit,
                    action="deficit_detected"
                )
            elif balance > 1000:
                excess = balance - 1000
                self._add_history(
                    "auto_balance",
                    hydra_id=state.business_type,
                    amount=excess,
                    action="excess_detected"
                )
        self.session.commit()
                
    def record_transaction(self, business_type: str, revenue: float, expenses: float = 0):
        """Registrar transacción financiera"""
        state = self._get_state(business_type)
        state.revenue += revenue
        state.expenses += expenses
        state.profit = state.revenue - state.expenses
        
        self.session.add(state)
        
        self._add_history(
            "transaction",
            business_type=business_type,
            revenue=revenue,
            expenses=expenses,
            profit=state.profit
        )
        self.session.commit()
        
        print(f"  [TESORO] Transacción registrada: {business_type} - Revenue: ${revenue}, Profit: ${state.profit}")

    def get_status(self):
        """Obtener estado completo del tesoro desde la base de datos"""
        states = self.session.query(TreasuryStateModel).all()
        funds_status = {}
        for state in states:
            funds_status[f"{state.business_type}_funds"] = state.profit
        
        # Get history count
        history_count = self.session.query(TreasuryHistoryModel).count()
        
        return {
            "financial_funds": funds_status.get("financial_funds", 0),
            "design_funds": funds_status.get("design_funds", 0),
            "trading_funds": funds_status.get("trading_funds", 0),
            "system_reserves": 0,
            "allocated_budgets": {state.business_type: state.budget for state in states},
            "history_count": history_count,
            "timestamp": datetime.utcnow().isoformat()
        }

# Singleton global treasury
# Note: In a web app, we should create a new controller per request or use dependency injection
# For backward compatibility, we keep a singleton but it's not thread-safe in web context
treasury = TreasuryController()
