# Sales Agent - Process Leads and Convert Customers with Database Persistence

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from database import SessionLocal, LeadModel, CustomerModel, BusinessModel

class SalesAgent:
    def __init__(self, business_type: str, price: float, session: Optional[SessionLocal] = None):
        self.business_type = business_type
        self.price = price
        self.session = session or SessionLocal()
        # Ensure business exists
        self.business = self.session.query(BusinessModel).filter(BusinessModel.business_type == business_type).first()
        if not self.business:
            raise ValueError(f"Business of type {business_type} not found in database")
    
    def add_lead(self, email: str, source: str = "Unknown") -> Dict[str, Any]:
        """Agregar un lead existente (ej. desde campañas de marketing) y guardarlo en la base de datos.
        En producción, los leads deben venir de fuentes reales como formularios web, eventos, etc.
        """
        lead_id = f"lead-{uuid.uuid4().hex[:8]}"
        
        # Validar email básico
        if lead_id.count("@") != 1 or "." not in lead_id.split("@")[1]:
            raise ValueError(f"Email inválido: {email}")
        
        # Crear registro de lead en base de datos
        db_lead = LeadModel(
            lead_id=lead_id,
            business_id=self.business.id,
            email=email,
            source=source,
            timestamp=datetime.utcnow(),
            qualified=False,
            score=0,
            value=self.price * 12  # Valor anual estimado
        )
        self.session.add(db_lead)
        self.session.commit()
        
        return {
            "id": db_lead.lead_id,
            "email": db_lead.email,
            "source": db_lead.source,
            "timestamp": db_lead.timestamp.isoformat(),
            "calificado": db_lead.qualified,
            "score": db_lead.score,
            "value": db_lead.value,
            "customer_id": db_lead.customer_id
        }
    
    def convert_lead(self, lead_id: str, payment_token: str) -> Dict[str, Any]:
        """Convertir un lead a cliente pagante procesando un pago real.
        REQUIRES REAL PAYMENT INTEGRATION (e.g., Stripe, PayPal).
        Este método actualmente lanza NotImplementedError porque se necesita integración real de pago.
        """
        # TODO: Implementar integración real de pago (Stripe, PayPal, etc.)
        # Por ahora, lanzamos una excepción para evitar simulaciones en producción
        raise NotImplementedError(
            "Integración de pago real requerida. "
            "Implementar el procesamiento de pagos mediante Stripe, PayPal u otro procesador. "
            "Proveer credenciales de API mediante variables de entorno o configuración."
        )
        
        # El siguiente código es un marcador de posición para cuando se implemente la integración real:
        # Obtener el lead de la base de datos
        db_lead = self.session.query(LeadModel).filter(LeadModel.lead_id == lead_id).first()
        if not db_lead:
            raise ValueError(f"Lead con ID {lead_id} no encontrado")
        
        # Procesar pago real (ejemplo con Stripe)
        # import stripe
        # stripe.api_key = get_stripe_api_key()
        # payment_intent = stripe.PaymentIntent.create(
        #     amount=int(self.price * 100),  # amount in cents
        #     currency="eur",
        #     payment_method=payment_token,
        #     confirm=True,
        #     return_url="https://yourdomain.com/payment_return"
        # )
        # 
        # Si el pago es exitoso, crear cliente
        # customer = stripe.Customer.create(
        #     email=db_lead.email,
        #     payment_method=payment_token
        # )
        # 
        # Crear registro de cliente en base de datos
        # db_customer = CustomerModel(
        #     customer_id=f"cust-{uuid.uuid4().hex[:8]}",
        #     business_id=self.business.id,
        #     email=db_lead.email,
        #     plan="monthly",
        #     price=self.price,
        #     start_date=datetime.utcnow(),
        #     status="active",
        #     stripe_customer_id=customer.id
        # )
        # self.session.add(db_customer)
        # 
        # Actualizar lead como convertido
        # db_lead.qualified = True
        # db_lead.score = 100
        # db_lead.customer_id = db_customer.customer_id
        # self.session.add(db_lead)
        # 
        # self.session.commit()
        # 
        # return {
        #     "id": db_customer.customer_id,
        #     "email": db_customer.email,
        #     "plan": db_customer.plan,
        #     "price": db_customer.price,
        #     "start_date": db_customer.start_date.isoformat(),
        #     "status": db_customer.status,
        #     "business_id": db_customer.business_id
        # }
        
    
    def get_metrics(self) -> Dict[str, Any]:
        """Obtener métricas de ventas desde la base de datos"""
        leads = self.session.query(LeadModel).filter(LeadModel.business_id == self.business.id).all()
        customers = self.session.query(CustomerModel).filter(CustomerModel.business_id == self.business.id).all()
        
        total_leads = len(leads)
        converted_leads = len([l for l in leads if l.qualified])
        conversion_rate = (converted_leads / total_leads * 100) if total_leads > 0 else 0
        
        return {
            "total_leads": total_leads,
            "converted_leads": converted_leads,
            "conversion_rate": round(conversion_rate, 2),
            "customers": len(customers),
            "revenue_potential": sum(l.value for l in leads),
            "revenue_real": sum(c.price * 12 for c in customers)  # Assuming annual revenue
        }

# Factory function para crear agente de ventas por tipo de negocio
def create_sales_agent(business_type: str, price: float, session: Optional[SessionLocal] = None) -> SalesAgent:
    return SalesAgent(business_type, price, session)
