# Referral Program Agent - Automated Referral and Affiliate Program

import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

from database import SessionLocal, BusinessModel, LeadModel, CustomerModel, TreasuryHistoryModel


class ReferralProgramAgent:
    def __init__(self, business_type: str, session: Optional[SessionLocal] = None):
        self.business_type = business_type
        self.session = session or SessionLocal()
        self.business = self.session.query(BusinessModel).filter(
            BusinessModel.business_type == business_type
        ).first()
        if not self.business:
            raise ValueError(f"Business of type {business_type} not found in database")
    
    def register_referrer(self, customer_id: str, referred_by: str) -> Dict[str, Any]:
        """Registrar un referido en el programa"""
        # Verificar que el cliente existe
        customer = self.session.query(CustomerModel).filter(
            CustomerModel.customer_id == customer_id
        ).first()
        
        if not customer:
            raise ValueError(f"Customer with ID {customer_id} not found")
        
        # Verificar quién referió
        referrer = self.session.query(BusinessModel).filter(
            BusinessModel.business_id == referred_by
        ).first()
        
        if not referrer:
            raise ValueError(f"Referrer with ID {referred_by} not found")
        
        # Registrar el referido en history
        referral = TreasuryHistoryModel(
            type="referral",
            timestamp=datetime.utcnow(),
            hydra_id=referred_by,
            amount=25.0,  # Transferencia estándar
            reason="referral_program",
            action="approved",
            message=f"Referido {customer_id} por {referred_by}",
            business_type=self.business_type,
            revenue=0.0,
            expenses=0.0,
            profit=25.0
        )
        self.session.add(referral)
        self.session.commit()
        
        return {
            "referral_id": referral.id,
            "referred_customer": customer_id,
            "referrer": referred_by,
            "amount_transferred": 25.0,
            "status": "completed",
            "message": "Referido registrado y beneficio transferido"
        }
    
    def track_referral_link(self, referrer_id: str) -> Dict[str, Any]:
        """Generar enlace de referido único"""
        referral_code = f"hydra_{referrer_id}_{uuid.uuid4().hex[:6]}"
        
        return {
            "referral_code": referral_code,
            "referrer_id": referrer_id,
            "share_url": f"https://hydra.business/refer?code={referral_code}",
            "status": "active",
            "message": "Enlace de referido generado"
        }
    
    def get_referral_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del programa de referidos"""
        referrals = self.session.query(TreasuryHistoryModel).filter(
            TreasuryHistoryModel.type == "referral",
            TreasuryHistoryModel.business_type == self.business_type
        ).all()
        
        total_referred = len(referrals)
        total_amount_transferred = sum(r.profit for r in referrals)
        
        new_customers = total_referred
        commission_revenue = total_amount_transferred * 0.10
        
        return {
            "total_referrals": total_referred,
            "new_customers": new_customers,
            "total_amount_transferred": round(total_amount_transferred, 2),
            "commission_earned": round(commission_revenue, 2),
            "conversion_rate": round((new_customers / max(1, total_referred)) * 100, 1),
            "program_status": "active" if total_referred > 0 else "pending"
        }


# Factory function para crear agente de referidos
def create_referral_program_agent(business_type: str, session: Optional[SessionLocal] = None) -> ReferralProgramAgent:
    return ReferralProgramAgent(business_type, session)