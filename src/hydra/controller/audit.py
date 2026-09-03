# Ecosystem Auditor - Financial Auditing and Validation with Database Persistence

import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from database import SessionLocal, AuditModel

class EcosystemAuditor:
    def __init__(self, session: Optional[SessionLocal] = None):
        self.session = session or SessionLocal()
        self.validation_rules = self._load_validation_rules()
        
    def _load_validation_rules(self) -> Dict[str, Any]:
        """Cargar reglas de validación para verificar ingresos reales"""
        return {
            "revenue_sources": [
                "suscription_fee",
                "service_delivery",
                "product_sales",
                "consulting_services"
            ],
            "minimum_monthly_revenue": 50,
            "maximum_fake_indicators": {
                "no_zero_revenue": True,
                "no_dummy_emails": True,
                "no_fake_company_names": True,
                "must_have_real_customers": True
            },
            "audit_frequency_hours": 24
        }
        
    def validate_transaction(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Validar una transacción financiera
        Verificar que todos los beneficios sean reales (no ficticios)
        """
        result = {
            "valid": True,
            "violations": [],
            "score": 100
        }
        
        # Verificar si es una entrada falsa
        if not transaction.get("real_customer", True):
            result["valid"] = False
            result["violations"].append("Falsa entrada detectada - no hay cliente real")
            result["score"] -= 50
            
        # Verificar email dummy
        email = transaction.get("customer_email", "")
        if "@example.com" in email or "dummy" in email.lower():
            result["valid"] = False
            result["violations"].append(f"Email dummy detectado: {email}")
            result["score"] -= 30
            
        # Verificar si hay revenue real
        if transaction.get("revenue", 0) <= 0:
            result["valid"] = False
            result["violations"].append("Revenue cero detectado")
            result["score"] -= 20
            
        # Verificar valor de transacción
        if transaction.get("value", 0) < 10:  # Mínimo $10 de valor
            result["valid"] = False
            result["violations"].append(f"Valor de transacción demasiado bajo: ${transaction.get('value', 0)}")
            result["score"] -= 10
            
        # Validar calidad del cliente
        customer_name = transaction.get("customer_name", "")
        if customer_name and len(customer_name) < 2:
            result["valid"] = False
            result["violations"].append(f"Nombre de cliente inválido: {customer_name}")
            result["score"] -= 10
            
        # Registrar auditoría
        self._record_audit("transaction_validation", {
            "transaction_id": transaction.get("id"),
            "result": result,
            "timestamp": datetime.utcnow()
        })
        
        return result
        
    def validate_hydra_profitability(self, hydra_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validar la rentabilidad de una HYDRA específica
        Asegurar consistencia del estado financiero
        """
        result = {
            "valid": True,
            "violations": [],
            "recommendations": []
        }
        
        # Verificar si tiene ingresos reales
        monthly_revenue = hydra_data.get("monthly_revenue", 0)
        if monthly_revenue < self.validation_rules["minimum_monthly_revenue"]:
            result["valid"] = False
            result["violations"].append(f"Revenue mensual insuficiente: ${monthly_revenue} (mínimo ${self.validation_rules['minimum_monthly_revenue']})")
            
        # Verificar relación ingresos-gastos
        revenue = hydra_data.get("revenue", 0)
        expenses = hydra_data.get("expenses", 0)
        if revenue > 0 and expenses >= revenue:
            result["valid"] = False
            result["violations"].append(f"Gastos exceden revenue: ${expenses} >= ${revenue}")
            
        # Verificar consistency de profit
        reported_profit = hydra_data.get("profit", 0)
        calculated_profit = revenue - expenses
        if abs(reported_profit - calculated_profit) > 1:
            result["valid"] = False
            result["violations"].append(f"Inconsistency de profit: reportado ${reported_profit}, calculado ${calculated_profit}")
            
        # Verificar si tiene clientes reales (no dummy)
        customers = hydra_data.get("customers", [])
        if customers:
            dummy_customers = [c for c in customers if "example.com" in c.get("email", "")]
            if dummy_customers:
                result["valid"] = False
                result["violations"].append(f"{len(dummy_customers)} clientes dummy detectados")
                
        # Registrar auditoría
        self._record_audit("hydra_validity", {
            "hydra_id": hydra_data.get("hydra_id"),
            "result": result,
            "timestamp": datetime.utcnow()
        })
        
        return result
        
    def perform_ecosystem_audit(self, businesses_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Realizar auditoría completa del ecosistema
        Revisar todas las HYDRAs y transacciones
        """
        overall_result = {
            "timestamp": datetime.utcnow(),
            "total_businesses": len(businesses_data),
            "valid_businesses": 0,
            "invalid_businesses": 0,
            "total_transactions": 0,
            "valid_transactions": 0,
            "audit_findings": [],
            "compliance_rate": 0
        }
        
        for business in businesses_data:
            # Validar HYDRA específica
            hydra_validation = self.validate_hydra_profitability(business)
            if hydra_validation["valid"]:
                overall_result["valid_businesses"] += 1
            else:
                overall_result["invalid_businesses"] += 1
                overall_result["audit_findings"].extend([
                    f"HYDRA {business.get('hydra_id', 'unknown')}: {violation}"
                    for violation in hydra_validation["violations"]
                ])
                
            # Validar transacciones si están presentes
            transactions = business.get("transactions", [])
            overall_result["total_transactions"] += len(transactions)
            
            for transaction in transactions:
                tx_result = self.validate_transaction(transaction)
                if tx_result["valid"]:
                    overall_result["valid_transactions"] += 1
                else:
                    overall_result["audit_findings"].extend([
                        f"Transacción {transaction.get('id', 'unknown')}: {violation}"
                        for violation in tx_result["violations"]
                    ])
                    
        # Calcular tasa de compliance
        total_items = overall_result["total_businesses"] + overall_result["total_transactions"]
        if total_items > 0:
            valid_items = overall_result["valid_businesses"] + overall_result["valid_transactions"]
            overall_result["compliance_rate"] = round((valid_items / total_items) * 100, 2)
            
        # Registrar auditoría del ecosistema
        self._record_audit("ecosystem_audit", overall_result)
        
        return overall_result
        
    def _record_audit(self, audit_type: str, data: Dict[str, Any]):
        """Registrar entrada de auditoría en la base de datos
        """
        audit_entry = AuditModel(
            type=audit_type,
            data=data,
            timestamp=datetime.utcnow(),
            auditor="system"
        )
        self.session.add(audit_entry)
        self.session.commit()
        
    def get_audit_log(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Obtener registro de auditoría para las últimas N horas desde la base de datos
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        audits = self.session.query(AuditModel).filter(AuditModel.timestamp >= cutoff_time).all()
        
        return [
            {
                "id": audit.id,
                "type": audit.type,
                "data": audit.data,
                "timestamp": audit.timestamp.isoformat(),
                "auditor": audit.auditor
            }
            for audit in audits
        ]

# Note: For use in web applications, it's better to create a new auditor per request or use dependency injection.
# For backward compatibility, we keep a singleton but it's not thread-safe in web context.
auditor = EcosystemAuditor()