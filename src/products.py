# Producto/Agentes de Producto para cada tipo de HYDRA

import uuid
from datetime import datetime
from typing import List, Dict, Any

class ProductAgent:
    def __init__(self, business_type: str, features: List[str], price: float):
        self.business_type = business_type
        self.product_id = f"prod-{business_type}-{uuid.uuid4().hex[:8]}"
        self.features = features
        self.price = price
        self.created_at = datetime.utcnow().isoformat()
        self.status = "development"
        
    def build_product(self, name: str, description: str) -> Dict[str, Any]:
        """Construir producto principal"""
        product = {
            "id": self.product_id,
            "name": name,
            "business_type": self.business_type,
            "description": description,
            "features": self.features,
            "price": self.price,
            "created_at": self.created_at,
            "status": "launched"
        }
        
        print(f"  [PRODUCTO] Construido: {name} (${self.price}/mes)")
        return product
    
    def get_product_spec(self) -> Dict[str, Any]:
        return {
            "product_id": self.product_id,
            "business_type": self.business_type,
            "name": f"{self.business_type.title()} Service",
            "price": self.price,
            "features": self.features,
            "created_at": self.created_at
        }

# Agentes de producto específicos por tipo de negocio
def create_product_agent(business_type: str) -> ProductAgent:
    if business_type == "financial":
        return ProductAgent(business_type, [
            "Dashboard de reporting financiero",
            "Balance automático", 
            "Reporte de ingresos/gastos",
            "Exportación a Excel",
            "Alertas personalizadas"
        ], 39.0)
    elif business_type == "design":
        return ProductAgent(business_type, [
            "Templates de diseño profesional",
            "Logo generator",
            "Plantillas de redes sociales",
            "Brand kits",
            "Edición rápida"
        ], 49.0)
    elif business_type == "trading":
        return ProductAgent(business_type, [
            "Gráficos de mercado en tiempo real",
            "Alertas de precios",
            "Análisis técnico básico",
            "Reportes diarios",
            "Exportación de datos"
        ], 29.0)
    else:
        return ProductAgent(business_type, [], 0.0)
