# Business Accounting - Ecosystem Financial Management with Database Persistence

import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from database import SessionLocal, BusinessModel, LeadModel, CustomerModel, AccountingReportModel

class BusinessAccounting:
    def __init__(self, session: Optional[SessionLocal] = None):
        self.session = session or SessionLocal()
        # No cache needed
        
    def generate_monthly_report(self, businesses_data: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Generar cierre financiero mensual automático obteniendo datos de la base de datos.
        El argumento businesses_data se mantiene por compatibilidad pero se ignora.
        """
        # Obtener todos los negocios de la base de datos
        businesses = self.session.query(BusinessModel).all()
        businesses_data = []
        for biz in businesses:
            # Calcular métricas mensuales
            monthly_revenue = biz.monthly_customers * biz.pricing if biz.monthly_customers and biz.pricing else 0.0
            # Nota: asumimos que los gastos son el 20% del ingreso (margen bruto 80%)
            expenses = monthly_revenue * 0.2
            profit = monthly_revenue - expenses
            businesses_data.append({
                "business_id": biz.business_id,
                "business_type": biz.business_type,
                "monthly_revenue": monthly_revenue,
                "expenses": expenses,
                "profit": profit,
                "active_subscriptions": biz.active_subscriptions,
                "previous_customers": 0  # No tenemos datos históricos por negocio aún
            })
        
        timestamp = datetime.utcnow()
        
        # Calcular métricas agregadas del ecosistema
        total_revenue = sum(b["monthly_revenue"] for b in businesses_data)
        total_expenses = sum(b["expenses"] for b in businesses_data)
        total_profit = sum(b["profit"] for b in businesses_data)
        total_customers = sum(b["active_subscriptions"] for b in businesses_data)
        
        # Calcular crecimiento y tendencias usando el reporte del mes anterior
        previous_month_data = self._get_previous_month_data()
        revenue_growth = self._calculate_growth_rate(
            total_revenue, 
            previous_month_data.get("total_revenue", 0)
        )
        customer_growth = self._calculate_growth_rate(
            total_customers,
            previous_month_data.get("total_customers", 0)
        )
        
        # Generar reporte detallado
        report = {
            "timestamp": timestamp.isoformat(),
            "period": self._get_current_month_info(),
            "summary": {
                "total_revenue": round(total_revenue, 2),
                "total_expenses": round(total_expenses, 2),
                "total_profit": round(total_profit, 2),
                "total_customers": total_customers,
                "profit_margin": round((total_profit / total_revenue * 100) if total_revenue > 0 else 0, 2),
                "average_revenue_per_customer": round((total_revenue / total_customers) if total_customers > 0 else 0, 2)
            },
            "by_business_type": self._segment_by_business_type(businesses_data),
            "growth_metrics": {
                "revenue_growth_rate": round(revenue_growth, 2),
                "customer_growth_rate": round(customer_growth, 2)
            },
            "performance_ranking": self._rank_by_performance(businesses_data),
            "financial_health": self._assess_financial_health(businesses_data)
        }
        
        # Guardar reporte en la base de datos
        self._save_report(report)
        
        return report
        
    def _segment_by_business_type(self, businesses_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Segmentar datos por tipo de negocio"""
        segments = {}
        
        for business in businesses_data:
            btype = business.get("business_type", "unknown")
            if btype not in segments:
                segments[btype] = {
                    "revenue": 0,
                    "expenses": 0,
                    "profit": 0,
                    "customers": 0,
                    "count": 0
                }
                
            segments[btype]["revenue"] += business.get("monthly_revenue", 0)
            segments[btype]["expenses"] += business.get("expenses", 0)
            segments[btype]["profit"] += business.get("profit", 0)
            segments[btype]["customers"] += business.get("active_subscriptions", 0)
            segments[btype]["count"] += 1
            
        # Calcular promedios
        for segment in segments.values():
            if segment["count"] > 0:
                segment["avg_revenue"] = round(segment["revenue"] / segment["count"], 2)
                segment["avg_customers"] = round(segment["customers"] / segment["count"], 2)
                
        return segments
        
    def _rank_by_performance(self, businesses_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calificar negocios por desempeño financiero"""
        ranked = []
        
        for business in businesses_data:
            # Calcular puntuación de desempeño (0-100)
            score = 0
            
            # Revenue (40% del peso)
            revenue_score = min(40, (business.get("monthly_revenue", 0) / 100) * 40)
            score += revenue_score
            
            # Margen de profit (30% del peso)
            revenue = business.get("monthly_revenue", 0)
            profit = business.get("profit", 0)
            margin = (profit / revenue * 100) if revenue > 0 else 0
            profit_score = min(30, margin)
            score += profit_score
            
            # Crecimiento de clientes (20% del peso)
            prev_customers = business.get("previous_customers", 0)
            curr_customers = business.get("active_subscriptions", 0)
            growth_rate = ((curr_customers - prev_customers) / prev_customers * 100) if prev_customers > 0 else 0
            customer_score = min(20, growth_rate)
            score += customer_score
            
            # Estabilidad (10% del peso)
            stability_score = 10 if business.get("profitable", True) else 0
            score += stability_score
            
            ranked.append({
                "business_id": business.get("business_id"),
                "business_type": business.get("business_type"),
                "performance_score": round(score, 2),
                "rank": len(ranked) + 1,
                "metrics": {
                    "monthly_revenue": business.get("monthly_revenue", 0),
                    "profit": business.get("profit", 0),
                    "customer_growth": growth_rate,
                    "profitable": business.get("profitable", True)
                }
            })
            
        # Ordenar por puntuación descendente
        ranked.sort(key=lambda x: x["performance_score"], reverse=True)
        return ranked
        
    def _assess_financial_health(self, businesses_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluar salud financiera general del ecosistema"""
        health_metrics = {
            "overall_score": 0,
            "risk_level": "low",
            "trends": [],
            "alerts": []
        }
        
        # Calcular puntaje general (0-100)
        total_score = 0
        business_count = len(businesses_data)
        
        for business in businesses_data:
            # Puntuación basada en varias métricas
            revenue = business.get("monthly_revenue", 0)
            profit = business.get("profit", 0)
            margin = (profit / revenue * 100) if revenue > 0 else 0
            
            # Normalizar cada factor (0-25 puntos cada)
            revenue_score = min(25, (revenue / 200) * 25)  # $200+ revenue máximo
            profit_score = min(25, margin)  # Margen de profit como puntuación
            stability_score = 25 if business.get("profitable", True) else 0
            
            total_score += revenue_score + profit_score + stability_score
            
        health_metrics["overall_score"] = round((total_score / (business_count * 25)) * 100, 2)
        
        # Determinar nivel de riesgo
        if health_metrics["overall_score"] >= 80:
            health_metrics["risk_level"] = "low"
        elif health_metrics["overall_score"] >= 60:
            health_metrics["risk_level"] = "medium"
        else:
            health_metrics["risk_level"] = "high"
            
        # Generar alertas si es necesario
        if business_count > 0:
            avg_revenue = sum(b.get("monthly_revenue", 0) for b in businesses_data) / business_count
            if avg_revenue < 25:
                health_metrics["alerts"].append({
                    "type": "low_revenue",
                    "message": f"Revenue promedio por negocio bajo: ${avg_revenue:.2f}",
                    "severity": "medium"
                })
                
            total_profit = sum(b.get("profit", 0) for b in businesses_data)
            if total_profit < 50:
                health_metrics["alerts"].append({
                    "type": "low_profit",
                    "message": f"Profit total del ecosistema bajo: ${total_profit:.2f} (objetivo: $50+)",
                    "severity": "high"
                })
                
        return health_metrics
        
    def _calculate_growth_rate(self, current: float, previous: float) -> float:
        """Calcular tasa de crecimiento desde período anterior"""
        if previous <= 0:
            return 0.0 if current <= 0 else 100.0
        return ((current - previous) / previous) * 100
        
    def _get_current_month_info(self) -> Dict[str, Any]:
        """Obtener información del mes actual"""
        now = datetime.utcnow()
        return {
            "year": now.year,
            "month": now.month,
            "month_name": now.strftime("%B"),
            "quarter": (now.month - 1) // 3 + 1
        }
        
    def _get_previous_month_data(self) -> Dict[str, Any]:
        """Obtener datos del mes anterior desde la base de datos"""
        # Obtener el reporte más reciente guardado
        latest_report = self.session.query(AccountingReportModel).order_by(AccountingReportModel.timestamp.desc()).first()
        if latest_report:
            return {
                "total_revenue": latest_report.total_revenue,
                "total_customers": latest_report.total_customers
            }
        # Si no hay reportes anteriores, retornar valores por defecto
        return {
            "total_revenue": 0.0,
            "total_customers": 0
        }
        
    def _save_report(self, report: Dict[str, Any]) -> None:
        """Guardar reporte en la base de datos"""
        report_db = AccountingReportModel(
            timestamp=datetime.fromisoformat(report["timestamp"]),
            period_year=report["period"]["year"],
            period_month=report["period"]["month"],
            period_month_name=report["period"]["month_name"],
            period_quarter=report["period"]["quarter"],
            total_revenue=report["summary"]["total_revenue"],
            total_expenses=report["summary"]["total_expenses"],
            total_profit=report["summary"]["total_profit"],
            total_customers=report["summary"]["total_customers"],
            profit_margin=report["summary"]["profit_margin"],
            average_revenue_per_customer=report["summary"]["average_revenue_per_customer"],
            report_data=report  # Guardar el reporte completo como JSON
        )
        self.session.add(report_db)
        self.session.commit()

# Singleton global accounting system
accounting = BusinessAccounting()