from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import stripe
import os
from datetime import datetime

from database import SessionLocal, TransactionModel

app = FastAPI(title="Hydra Product API")

# Configure Stripe API key from environment variable
stripe_api_key = os.getenv("STRIPE_API_KEY")
if stripe_api_key:
    stripe.api_key = stripe_api_key
else:
    # In production, we should not allow missing API key
    # For now, we'll raise an error if not configured
    pass

class PurchaseRequest(BaseModel):
    customer_email: str
    amount_eur: float

@app.post("/purchase")
def purchase(req: PurchaseRequest):
    """Crear un intento de pago real usando Stripe.
    REQUIRES STRIPE API KEY CONFIGURADA.
    """
    if not stripe_api_key:
        raise HTTPException(
            status_code=503,
            detail="Stripe API key not configured. Please set STRIPE_API_KEY environment variable."
        )
    
    try:
        # Crear un PaymentIntent de Stripe
        intent = stripe.PaymentIntent.create(
            amount=int(req.amount_eur * 100),  # convert to cents
            currency="eur",
            receipt_email=req.customer_email,
        )
        
        # Guardar la transacción en la base de datos (pendiente de pago)
        db = SessionLocal()
        transaction = TransactionModel(
            business_type="unknown",  # TODO: determinar desde el contexto
            revenue=0.0,  # aún no se ha completado el pago
            expenses=0.0,
            profit=0.0,
            description=f"PaymentIntent {intent.id} for email {req.customer_email}, amount {req.amount_eur} EUR"
        )
        db.add(transaction)
        db.commit()
        db.close()
        
        return {
            "client_secret": intent.client_secret,
            "payment_intent_id": intent.id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Endpoint para confirmar pago (webhook o retorno)
@app.post("/payment/confirm")
def confirm_payment(payment_intent_id: str):
    """Confirmar que un pago se ha completado exitosamente."""
    if not stripe_api_key:
        raise HTTPException(
            status_code=503,
            detail="Stripe API key not configured."
        )
    try:
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        if intent.status == "succeeded":
            # Actualizar la transacción en la base de datos como completada
            db = SessionLocal()
            transaction = db.query(TransactionModel).filter(
                TransactionModel.description.like(f"%{payment_intent_id}%")
            ).first()
            if transaction:
                # Extraer amount y email de la descripción (mejoraría con un modelo mejor)
                # Por ahora, simplemente marcamos como completado
                transaction.revenue = float(intent.amount) / 100  # convert back to EUR
                transaction.profit = transaction.revenue  # simplificado
                db.commit()
            db.close()
            return {"status": "success", "message": "Payment confirmed"}
        else:
            return {"status": intent.status, "message": "Payment not yet succeeded"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
