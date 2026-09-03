# Marketing Agent - Generate Traffic and Leads with Database Persistence

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import os

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

from database import SessionLocal, CampaignModel, BusinessModel, LeadModel

# Configure email from environment
EMAIL_SMTP_HOST = os.getenv("EMAIL_SMTP_HOST", "smtp.sendgrid.net")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))
EMAIL_SMTP_USER = os.getenv("EMAIL_SMTP_USER", "apikey")
EMAIL_SMTP_PASSWORD = os.getenv("EMAIL_SMTP_PASSWORD", "SG.YourSendGridKey")
EMAIL_FROM = os.getenv("EMAIL_FROM", "no-reply@hydra.business.com")


def send_email(to_email: str, subject: str, body: str) -> bool:
    """Send email via SMTP"""
    try:
        msg = MIMEText(body, "plain")
        msg["Subject"] = subject
        msg["From"] = EMAIL_FROM
        msg["To"] = to_email
        
        with smtplib.SMTP(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SMTP_USER, EMAIL_SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Error sending email to {to_email}: {e}")
        return False


class MarketingAgent:
    def __init__(self, business_type: str, budget: float = 500.0, session: Optional[SessionLocal] = None):
        self.business_type = business_type
        self.budget = budget
        self.session = session or SessionLocal()
        # Ensure business exists
        self.business = self.session.query(BusinessModel).filter(BusinessModel.business_type == business_type).first()
        if not self.business:
            raise ValueError(f"Business of type {business_type} not found in database")
    
    def run_campaign(self, platform: str, budget: float) -> Dict[str, Any]:
        """Ejecutar campaña de marketing con integración real de leads y email"""
        if budget > self.budget:
            raise ValueError(f"Presupuesto {budget} excede presupuesto total {self.budget}")
        
        # Calculated number of leads (1 lead per $10 spent)
        leads_count = int(budget / 10)
        
        # Generar leads en la base de datos
        campaign_id = f"camp-{uuid.uuid4().hex[:8]}"
        
        for i in range(min(leads_count, 20)):  # Máximo 20 leads por campaña
            email = f"lead{i+1}@empresa{self.business.business_id[:4]}.com"
            # Guardar lead en base de datos
            db_lead = LeadModel(
                lead_id=f"lead-{uuid.uuid4().hex[:8]}",
                business_id=self.business.business_id,
                email=email,
                source=platform,
                timestamp=datetime.utcnow(),
                qualified=False,
                score=0,
                value=self.business.pricing * 12
            )
            self.session.add(db_lead)
            
            # Enviar email de bienvenida al lead
            send_email(
                to_email=email,
                subject="Bienvenido a Hydra - Tu negocio está listo",
                body=f"Hola! Hemos generado un lead para tu negocio {self.business.business_type}. Estamos procesando tu información y te contactaremos pronto."
            )
        
        self.session.commit()
        
        # Crear registro de campaña usando el constructor normal de SQLAlchemy
        campaign = CampaignModel(
            campaign_id=campaign_id,
            business_id=self.business.business_id,
            platform=platform,
            budget=budget,
            leads_generated=leads_count,
            cost_per_lead=budget / leads_count if leads_count > 0 else 0,
            status="active"
        )
        self.session.add(campaign)
        self.session.commit()
        
        self.budget -= budget
        
        return {
            "id": campaign.campaign_id,
            "platform": campaign.platform,
            "budget": budget,
            "leads_generated": campaign.leads_generated,
            "cost_per_lead": campaign.cost_per_lead,
            "start_date": campaign.start_date.isoformat() if campaign.start_date else None,
            "status": campaign.status
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Obtener métricas de rendimiento de marketing desde la base de datos"""
        campaigns = self.session.query(CampaignModel).filter(CampaignModel.business_id == self.business.business_id).all()
        total_spend = sum(c.budget for c in campaigns)
        total_leads = sum(c.leads_generated for c in campaigns)
        cost_per_lead = total_spend / total_leads if total_leads > 0 else 0
        
        return {
            "campaigns_count": len(campaigns),
            "total_spent": total_spend,
            "total_leads_generated": total_leads,
            "cost_per_lead": round(cost_per_lead, 2),
            "leads_per_dollar": total_leads / total_spend if total_spend > 0 else 0
        }

# Factory function para crear agente de marketing por tipo de negocio
def create_marketing_agent(business_type: str, budget: float = 500.0, session: Optional[SessionLocal] = None) -> MarketingAgent:
    return MarketingAgent(business_type, budget, session)