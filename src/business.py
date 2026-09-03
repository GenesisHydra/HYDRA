# Hydra Business Module - Core Business Logic with Database Persistence

import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

from database import SessionLocal, BusinessModel, LeadModel, CustomerModel

class Business:
    """Core business logic for each HYDRA with database persistence"""
    
    def __init__(self, business_type: str, initial_capital: float = 0.0, session: Optional[SessionLocal] = None, business_id: Optional[str] = None):
        """
        Initialize a business.
        If session and business_id are provided, load existing business.
        Otherwise, create a new business.
        """
        self.business_type = business_type
        self.session = session or SessionLocal()
        
        if business_id:
            # Load existing business
            self._load_from_db(business_id)
        else:
            # Create new business
            self.business_id = f"{business_type}-{uuid.uuid4().hex[:8]}"
            self.capital = initial_capital
            self.revenue = 0.0
            self.expenses = 0.0
            self.profit = 0.0
            self.created_at = datetime.utcnow()
            
            # Initialize based on business type
            self._setup_product()
            self._setup_operations()
            
            # Save to database
            self._save_to_db()
    
    def _load_from_db(self, business_id: str):
        """Load business state from database"""
        db_business = self.session.query(BusinessModel).filter(BusinessModel.business_id == business_id).first()
        if not db_business:
            raise ValueError(f"Business with ID {business_id} not found")
        
        self.business_id = db_business.business_id
        self.business_type = db_business.business_type
        self.capital = db_business.capital
        self.revenue = db_business.revenue
        self.expenses = db_business.expenses
        self.profit = db_business.profit
        self.created_at = db_business.created_at
        self.product_name = db_business.product_name
        self.pricing = db_business.pricing
        self.target_customers = db_business.target_customers
        self.features = db_business.features or []
        self.customer_base_size = db_business.customer_base_size
        self.conversion_rate = db_business.conversion_rate
        self.monthly_customers = db_business.monthly_customers
        self.active_subscriptions = db_business.active_subscriptions
        self.sales_count = db_business.sales_count
        self.customer_satisfaction_score = db_business.customer_satisfaction_score
        
        # Load leads and customers (we'll keep them in memory for now, but could load on demand)
        self._load_leads_and_customers()
    
    def _load_leads_and_customers(self):
        """Load leads and customers into memory lists for quick access"""
        db_leads = self.session.query(LeadModel).filter(LeadModel.business_id == self.id).all()
        self.leads = []
        for lead in db_leads:
            self.leads.append({
                "id": lead.lead_id,
                "email": lead.email,
                "source": lead.source,
                "timestamp": lead.timestamp.isoformat() if lead.timestamp else None,
                "calificado": lead.qualified,
                "score": lead.score,
                "value": lead.value,
                "customer_id": lead.customer_id
            })
        
        db_customers = self.session.query(CustomerModel).filter(CustomerModel.business_id == self.id).all()
        self.customers = []  # We might not need to keep customers in memory, but we'll keep for compatibility
        for customer in db_customers:
            self.customers.append({
                "id": customer.customer_id,
                "email": customer.email,
                "plan": customer.plan,
                "price": customer.price,
                "start_date": customer.start_date.isoformat() if customer.start_date else None,
                "status": customer.status
            })
    
    def _get_db_id(self) -> int:
        """Get the database ID for this business"""
        db_business = self.session.query(BusinessModel).filter(BusinessModel.business_id == self.business_id).first()
        return db_business.business_id if db_business else None
    
    def _save_to_db(self):
        """Save or update business state in database"""
        db_business = self.session.query(BusinessModel).filter(BusinessModel.business_id == self.business_id).first()
        if not db_business:
            # Create new record
            db_business = BusinessModel(
                business_id=self.business_id,
                business_type=self.business_type,
                capital=self.capital,
                revenue=self.revenue,
                expenses=self.expenses,
                profit=self.profit,
                created_at=self.created_at,
                product_name=self.product_name,
                pricing=self.pricing,
                target_customers=self.target_customers,
                features=self.features,
                customer_base_size=self.customer_base_size,
                conversion_rate=self.conversion_rate,
                monthly_customers=self.monthly_customers,
                active_subscriptions=self.active_subscriptions,
                sales_count=self.sales_count,
                customer_satisfaction_score=self.customer_satisfaction_score
            )
            self.session.add(db_business)
        else:
            # Update existing record
            db_business.capital = self.capital
            db_business.revenue = self.revenue
            db_business.expenses = self.expenses
            db_business.profit = self.profit
            db_business.product_name = self.product_name
            db_business.pricing = self.pricing
            db_business.target_customers = db_business.target_customers
            db_business.features = self.features
            db_business.customer_base_size = db_business.customer_base_size
            db_business.conversion_rate = db_business.conversion_rate
            db_business.monthly_customers = self.monthly_customers
            db_business.active_subscriptions = db_business.active_subscriptions
            db_business.sales_count = db_business.sales_count
            db_business.customer_satisfaction_score = self.customer_satisfaction_score
        
        self.session.commit()
    
    def _setup_product(self):
        """Configure the product/service based on business type"""
        if self.business_type == "financial":
            self.product_name = "Reporting Automatizado para PYMES"
            self.pricing = 39.0  # $39/mes
            self.target_customers = "Contadores, CFOs de startups, empresarios"
            self.features = [
                "Balance automático",
                "Reporte de ingresos/gastos", 
                "Cash flow",
                "Exportación a Excel",
                "Panel de control"
            ]
            self.customer_base_size = 1000
            self.conversion_rate = 0.05
            
        elif self.business_type == "design":
            self.product_name = "Templates Profesionales de Diseño"
            self.pricing = 49.0  # $49/paquete de 3 diseños
            self.target_customers = "Fundadores de startups, diseñadores junior"
            self.features = [
                "Logo profesional",
                "Tarjeta de presentación",
                "Flyer/redes sociales",
                "Brand kit"
            ]
            self.customer_base_size = 800
            self.conversion_rate = 0.08
            
        elif self.business_type == "trading":
            self.product_name = "Dashboard de Análisis de Mercado"
            self.pricing = 29.0  # $29/mes
            self.target_customers = "Inversores individuales, small business"
            self.features = [
                "Gráficos de acciones",
                "Indicadores clave",
                "Alertas automáticas",
                "Reportes mensuales"
            ]
            self.customer_base_size = 1200
            self.conversion_rate = 0.06
    
    def _setup_operations(self):
        """Configurar operaciones del negocio"""
        self.monthly_customers = 0
        self.active_subscriptions = 0
        self.leads = []  # We'll keep leads in memory for quick access, but they are also in DB
        self.sales_count = 0
        self.customer_satisfaction_score = 0
    
    def analyze_market(self) -> Dict[str, Any]:
        """Analizar el mercado para este tipo de negocio"""
        total_market_size = {
            "financial": 50000000,
            "design": 35000000,
            "trading": 40000000
        }
        
        return {
            "market_type": "B2B servicios para PYMES",
            "total_market_size_usd": total_market_size.get(self.business_type, 0),
            "tam_size_usd": total_market_size.get(self.business_type, 0) * 0.01,  # Top 1%
            "sam_size_usd": total_market_size.get(self.business_type, 0) * 0.03,  # Mercado accesible
            "som_size_usd": total_market_size.get(self.business_type, 0) * 0.08,  # Mercado objetivo
            "competencia_principal": self._get_main_competitors(),
            "oportunidad": self._identify_market_opp(),
            "tasa_conversion_promedio": self.conversion_rate
        }
    
    def _get_main_competitors(self) -> List[str]:
        if self.business_type == "financial":
            return ["QuickBooks", "Xero", "Wave"]
        elif self.business_type == "design":
            return ["Canva", "Fiverr Pro", "99designs"]
        elif self.business_type == "trading":
            return ["TradingView", "Yahoo Finance", "Bloomberg Terminal"]
        return []
    
    def _identify_market_opp(self) -> str:
        opportunities = {
            "financial": "Automatización de reportes para contadores freelancers",
            "design": "Templates profesionales rápidos para startups",
            "trading": "Análisis de mercado básico a bajo costo"
        }
        return opportunities.get(self.business_type, "Mercado no identificado")
    
    def generate_lead(self, source: str, email: str) -> Dict[str, Any]:
        """Generar un lead calificado y guardarlo en la base de datos"""
        lead_id = f"lead-{uuid.uuid4().hex[:8]}"
        lead = {
            "id": lead_id,
            "email": email,
            "source": source,
            "timestamp": datetime.utcnow().isoformat(),
            "calificado": False,
            "score": 0,
            "value": self.pricing * 12  # Valor anual estimado
        }
        
        # Save to database
        db_lead = LeadModel(
            lead_id=lead_id,
            business_id=self._get_db_id(),
            email=email,
            source=source,
            timestamp=datetime.utcnow(),
            qualified=False,
            score=0,
            value=self.pricing * 12
        )
        self.session.add(db_lead)
        self.session.commit()
        
        # Add to memory list
        self.leads.append(lead)
        return lead
    
    def convert_lead(self, lead_id: str) -> Optional[Dict[str, Any]]:
        """Convertir un lead a cliente pagante y guardar en base de datos"""
        # Find lead in memory first
        lead = next((l for l in self.leads if l["id"] == lead_id), None)
        if not lead:
            # Try to load from database
            db_lead = self.session.query(LeadModel).filter(LeadModel.lead_id == lead_id).first()
            if not db_lead:
                return None
            # Convert db_lead to dict format
            lead = {
                "id": db_lead.lead_id,
                "email": db_lead.email,
                "source": db_lead.source,
                "timestamp": db_lead.timestamp.isoformat() if db_lead.timestamp else None,
                "calificado": db_lead.qualified,
                "score": db_lead.score,
                "value": db_lead.value,
                "customer_id": db_lead.customer_id
            }
        
        # Verificar si el lead está calificado (basado en criterios simples)
        if lead["email"].count("@") == 1 and "." in lead["email"].split("@")[1]:
            # Generar suscripción
            subscription_id = f"sub-{uuid.uuid4().hex[:8]}"
            customer = {
                "id": subscription_id,
                "email": lead["email"],
                "plan": "monthly",
                "price": self.pricing,
                "start_date": datetime.utcnow().isoformat(),
                "status": "active"
            }
            
            # Update lead as qualified in database
            db_lead = self.session.query(LeadModel).filter(LeadModel.lead_id == lead_id).first()
            if db_lead:
                db_lead.qualified = True
                db_lead.score = 100
                db_lead.customer_id = subscription_id
                self.session.add(db_lead)
            
            # Save customer to database
            db_customer = CustomerModel(
                customer_id=subscription_id,
                business_id=self._get_db_id(),
                email=lead["email"],
                plan="monthly",
                price=self.pricing,
                start_date=datetime.utcnow(),
                status="active"
            )
            self.session.add(db_customer)
            
            # Update business metrics
            
            
            # Update lead in memory
            lead["calificado"] = True
            lead["score"] = 100
            lead["customer_id"] = subscription_id
            
            self.session.commit()
            
            return customer
            
        return None
    
    def generate_sales(self, number_of_customers: int) -> float:
        """Generar ventas mensuales y actualizar base de datos"""
        if number_of_customers <= 0:
            return 0.0
            
        revenue = number_of_customers * self.pricing
        self.revenue += revenue
        self.monthly_customers += number_of_customers
        self.active_subscriptions += number_of_customers
        self.sales_count += number_of_customers
        
        # Update business in database
        self._save_to_db()
        
        return revenue
    
    def calculate_monthly_metrics(self, marketing_cost: float = 0.0) -> Dict[str, Any]:
        """Calcular métricas financieras y de negocio"""
        monthly_revenue = self.monthly_customers * self.pricing
        gross_margin = monthly_revenue * 0.80  # 80% margen bruto asumido
        net_profit = gross_margin - marketing_cost
        
        # Calcular KPIs
        cac = marketing_cost / max(1, self.sales_count) if self.sales_count > 0 else 0
        ltv = self.pricing * 12 * 0.7  # Valor de vida del cliente estimado
        ltv_cac_ratio = ltv / cac if cac > 0 else 0
        monthly_recurring_revenue = self.active_subscriptions * self.pricing
        
        return {
            "business_id": self.business_id,
            "business_type": self.business_type,
            "timestamp": datetime.utcnow().isoformat(),
            "monthly_revenue": round(monthly_revenue, 2),
            "monthly_customers": self.monthly_customers,
            "active_subscriptions": self.active_subscriptions,
            "sales_count": self.sales_count,
            "marketing_cost": marketing_cost,
            "gross_margin": round(gross_margin, 2),
            "net_profit": round(net_profit, 2),
            "cac": round(cac, 2),
            "ltv": round(ltv, 2),
            "ltv_cac_ratio": round(ltv_cac_ratio, 2),
            "mr_revenue": round(monthly_recurring_revenue, 2),
            "customer_acquisition_rate": round(self.sales_count / max(1, len(self.leads)), 4) if self.leads else 0,
            "product_name": self.product_name,
            "pricing": self.pricing,
            "features_count": len(self.features),
            "profitable": net_profit >= 50,
            "can_reproduce": net_profit >= 50
        }
    
    def run_business_cycle(self, marketing_budget: float = 500.0) -> Dict[str, Any]:
        """Ejecutar un ciclo completo de negocio (mensual)"""
        # Generar leads basado en presupuesto de marketing
        leads_generated = int(marketing_budget / 10)  # Aproximadamente 1 lead por $10 gastados
        new_leads = []
        for i in range(min(leads_generated, 20)):  # Máximo 20 leads por ciclo
            lead = self.generate_lead(
                source="LinkedIn Ads",
                email=f"lead{i+1}@empresa{self.business_id[:4]}.com"
            )
            new_leads.append(lead)
        
        # Convertir algunos leads
        converted_customers = 0
        for lead in new_leads[:min(3, len(new_leads))]:
            customer = self.convert_lead(lead["id"])
            if customer:
                converted_customers += 1
        
        # Generar revenue
        print(f"Converted customers: {converted_customers}")
        monthly_revenue = self.generate_sales(converted_customers)
        
        # Calcular métricas
        metrics = self.calculate_monthly_metrics(marketing_budget)
        
        # Actualizar profit
        self.profit += metrics["net_profit"]
        self.capital += metrics["net_profit"]
        
        self._save_to_db()
        # self._save_state()
        
        return metrics
    
    def _save_state(self):
        """Guardar estado del negocio (deprecated, use _save_to_db)"""
        # Keep for backward compatibility but delegate to database
        self._save_to_db()
    
    def get_status(self) -> Dict[str, Any]:
        """Obtener estado actual del negocio"""
        # Ensure we have latest data from database
        db_business = self.session.query(BusinessModel).filter(BusinessModel.business_id == self.business_id).first()
        if db_business:
            self.capital = db_business.capital
            self.profit = db_business.profit
            self.monthly_customers = db_business.monthly_customers
            self.active_subscriptions = db_business.active_subscriptions
            self.sales_count = db_business.sales_count
        
        return {
            "business_id": self.business_id,
            "business_type": self.business_type,
            "capital": self.capital,
            "profit": self.profit,
            "monthly_customers": self.monthly_customers,
            "active_subscriptions": self.active_subscriptions,
            "sales_count": self.sales_count,
            "product_name": self.product_name,
            "pricing": self.pricing,
            "revenue_this_month": self.monthly_customers * self.pricing,
            "profitable": self.profit >= 50,
            "can_reproduce": self.profit >= 50
        }
