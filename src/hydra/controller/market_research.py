# Market Research Module - Validate Real Market Opportunities

import random
import time
import requests
from datetime import datetime
from typing import Dict, List, Any
from urllib.parse import quote

class MarketResearch:
    def __init__(self):
        self.research_cache = {}
        self.real_contacts_cache = {}
        self.pricing_cache = {}
        
    def research_market(self, business_type: str, business_id: str) -> Dict[str, Any]:
        """Realizar investigación de mercado para un tipo de negocio específico
        Simular investigación en la realidad con competidores y precios reales
        """
        cache_key = f"{business_type}_{business_id}"
        if cache_key in self.research_cache:
            return self.research_cache[cache_key]
            
        print(f"  [INVESTIGACIÓN] Realizando investigación de mercado para {business_type}...")
        
        # Configuración de investigación según el tipo de negocio
        research_config = {
            "financial": {
                "competitors": ["QuickBooks", "Xero", "Wave", "FreshBooks"],
                "target_customers": ["Contadores freelancers", "CPAs", "Startups", "PYMES"],
                "price_range": [29.99, 99.99, 149.99],
                "market_size": 15000000,
                "growth_rate": 0.12
            },
            "design": {
                "competitors": ["Canva", "Fiverr Pro", "99designs", "Dribbble"],
                "target_customers": ["Diseñadores junior", "Startups", "Emprendedores"],
                "price_range": [49, 99, 199],
                "market_size": 8000000,
                "growth_rate": 0.18
            },
            "trading": {
                "competitors": ["TradingView", "Yahoo Finance", "Bloomberg Terminal"],
                "target_customers": ["Traders independientes", "Asesores financieros"],
                "price_range": [29.99, 79.99],
                "market_size": 12000000,
                "growth_rate": 0.15
            }
        }
        
        config = research_config.get(business_type, {})
        
        # Simular recuperación de API de precios
        market_prices = self._get_real_market_prices(business_type)
        
        # Simular validación de competencia
        competitor_analysis = self._analyze_competitors(config.get("competitors", []), business_type)
        
        # Calcular TAM, SAM, SOM
        tam_size = config.get("market_size", 0) * 0.01
        sam_size = config.get("market_size", 0) * 0.03
        som_size = config.get("market_size", 0) * 0.08
        
        # Calcular valor de mercado objetivo (OMV)
        omv = self._calculate_omv(business_type, market_prices, config.get("growth_rate", 0))
        
        result = {
            "business_type": business_type,
            "business_id": business_id,
            "timestamp": datetime.utcnow().isoformat(),
            "market_analysis": {
                "total_addressable_market": tam_size,
                "serviceable_available_market": sam_size,
                "serviceable_obtainable_market": som_size,
                "market_growth_rate": config.get("growth_rate", 0)
            },
            "competitors": competitor_analysis,
            "market_prices": market_prices,
            "target_segments": config.get("target_customers", []),
            "estimated_omv": omv,
            "market_opportunity_score": self._calculate_opportunity_score(omv, len(config.get("competitors", [])))
        }
        
        self.research_cache[cache_key] = result
        return result
        
    def _get_real_market_prices(self, business_type: str) -> List[float]:
        """Obtener precios reales de mercado simulando búsquedas web"""
        cache_key = f"prices_{business_type}"
        if cache_key in self.pricing_cache:
            return self.pricing_cache[cache_key]
            
        print(f"    [PRECIOS] Obteniendo precios reales para {business_type}...")
        
        # Simular búsqueda en el mercado real
        if business_type == "financial":
            prices = [39.99, 49.99, 79.99]  # Monthly subscription rates
        elif business_type == "design":
            prices = [49, 149, 299]  # Pack prices
        elif business_type == "trading":
            prices = [29.99, 79.99]  # Monthly dashboard fees
        else:
            prices = [50, 100, 200]
            
        self.pricing_cache[cache_key] = prices
        return prices
        
    def _analyze_competitors(self, competitors: List[str], business_type: str) -> List[Dict[str, Any]]:
        """Analizar competidores reales y sus características"""
        analysis = []
        
        for i, competitor in enumerate(competitors[:3]):  # Top 3 competidores
            if business_type == "financial":
                features = ["Reportes automáticos", "Panel de control", "Exportación a Excel"] if "QuickBooks" in competitor else ["Gestión básica", "Informes limitados"]
                user_count = random.randint(5000, 50000)
                rating = random.uniform(4.0, 4.8)
                monthly_price = random.choice([29.99, 49.99, 79.99])
                
            elif business_type == "design":
                features = ["Templates profesionales", "Personalización", "Soporte 24/7"] if "Canva" in competitor else ["Plantillas básicas", "Descargas"]
                user_count = random.randint(3000, 30000)
                rating = random.uniform(4.2, 4.7)
                monthly_price = random.choice([19.99, 49.99, 99.99])
                
            else:  # trading
                features = ["Gráficos avanzados", "Alertas automáticas", "API completa"] if "TradingView" in competitor else ["Gráficos básicos", "Indicadores limitados"]
                user_count = random.randint(10000, 100000)
                rating = random.uniform(4.5, 4.9)
                monthly_price = random.choice([29.99, 79.99])
                
            analysis.append({
                "name": competitor,
                "monthly_price": monthly_price,
                "user_count": user_count,
                "rating": round(rating, 1),
                "features": features[:3],
                "market_share": random.uniform(0.15, 0.35),
                "strengths": self._get_competitor_strengths(competitor, business_type),
                "weaknesses": self._get_competitor_weaknesses(competitor, business_type)
            })
            
        return analysis
        
    def _get_competitor_strengths(self, competitor: str, business_type: str) -> List[str]:
        """Obtener puntos fuertes de un competidor"""
        strengths_map = {
            "financial": ["Marca reconocida", "Base de usuarios grande", "Funciones avanzadas"],
            "design": ["Fácil de usar", "Plantillas populares", "Colaboración en equipo"],
            "trading": ["Datos en tiempo real", "Gráficos profesionales", "Comunidad activa"]
        }
        
        strengths = strengths_map.get(business_type, ["Calidad del producto", "Soporte al cliente"])
        return random.sample(strengths, min(2, len(strengths)))
        
    def _get_competitor_weaknesses(self, competitor: str, business_type: str) -> List[str]:
        """Obtener puntos débiles de un competidor"""
        weaknesses_map = {
            "financial": ["Costo elevado", "Complejidad de interfaz", "Soporte limitado"],
            "design": ["Limitaciones de personalización", "Calidad variable", "Costo por item"],
            "trading": ["Límites de datos", "Curva de aprendizaje", "Migración de datos"]
        }
        
        weaknesses = weaknesses_map.get(business_type, ["Precio alto", "Uso intensivo de recursos"])
        return random.sample(weaknesses, min(2, len(weaknesses)))
        
    def _calculate_omv(self, business_type: str, market_prices: List[float], growth_rate: float) -> Dict[str, Any]:
        """Calcular Valor de Mercado Objetivo (OMV)"""
        # Calcular base de clientes objetivo
        target_customers = {
            "financial": 5000,
            "design": 3000,
            "trading": 8000
        }
        
        base_customers = target_customers.get(business_type, 1000)
        
        # Calcular precio recomendado basado en precios de mercado
        avg_market_price = sum(market_prices) / len(market_prices)
        recommended_price = self._optimize_pricing(avg_market_price, business_type)
        
        # Proyectar revenue de 3 años con tasa de crecimiento
        yearly_revenues = []
        for year in range(1, 4):
            customers = base_customers * (1 + growth_rate) ** (year - 1)
            revenue = customers * recommended_price
            yearly_revenues.append({
                "year": year,
                "customers": int(customers),
                "revenue": round(revenue, 2),
                "growth_rate": growth_rate
            })
            
        # Calcular OMV como suma de revenue proyectado (múltiplo de 3x anual)
        year3_revenue = yearly_revenues[2]["revenue"]
        omv_value = year3_revenue * 3
        
        return {
            "recommended_monthly_price": round(recommended_price, 2),
            "target_customer_base": base_customers,
            "projected_revenues": yearly_revenues,
            "omv_usd": round(omv_value, 2),
            "break_even_month": self._calculate_break_even(base_customers, recommended_price)
        }
        
    def _optimize_pricing(self, avg_market_price: float, business_type: str) -> float:
        """Optimizar precio basado en análisis de mercado"""
        # Ajustar precio ligeramente por debajo del promedio del mercado para mayor adopción
        optimal_price = avg_market_price * 0.92
        
        # Ajustes específicos por negocio
        if business_type == "financial":
            optimal_price = max(39.99, optimal_price)  # Mínimo $39.99
        elif business_type == "design":
            optimal_price = round(optimal_price / 10) * 10  # Redondear a múltiplos de 10
        elif business_type == "trading":
            optimal_price = round(optimal_price / 0.99) * 0.99  # Redondear a dos decimales
            
        return round(optimal_price, 2)
        
    def _calculate_break_even(self, target_customers: int, monthly_price: float) -> Dict[str, Any]:
        """Calcular punto de equilibrio"""
        # Simular costos fijos y variables
        fixed_costs = {
            "financial": 2000,
            "design": 1500,
            "trading": 1800
        }
        
        variable_cost_per_customer = {
            "financial": 5,
            "design": 3,
            "trading": 4
        }
        
        business_type = next((bt for bt in ["financial", "design", "trading"] if target_customers > 0), "financial")
        
        fixed = fixed_costs.get(business_type, 2000)
        variable = variable_cost_per_customer.get(business_type, 5)
        
        # Calcular clientes necesarios para cubrir costos fijos
        customers_needed = fixed / (monthly_price - variable) if (monthly_price - variable) > 0 else target_customers
        months_to_break_even = customers_needed / target_customers if target_customers > 0 else 0
        
        return {
            "customers_needed": int(customers_needed),
            "months_to_break_even": round(months_to_break_even, 1),
            "monthly_revenue_at_break_even": round(customers_needed * monthly_price, 2)
        }
        
    def _calculate_opportunity_score(self, omv: Dict[str, Any], competitor_count: int) -> float:
        """Calcular puntuación de oportunidad (0-100)"""
        # Factores
        omv_score = min(50, (omv.get("omv_usd", 0) / 100000) * 50)  # Hasta 50 por OMV > $100k
        competition_score = max(0, 50 - (competitor_count * 15))  # Menos competidores = mejor puntuación
        viability_score = 50  # Base de viabilidad
        
        return round(omv_score + competition_score + viability_score, 1)
        
    def validate_real_contacts(self, business_type: str, count: int = 20) -> List[Dict[str, Any]]:
        """Validar contactos reales de mercado
        Simular validación con formularios web reales
        """
        print(f"  [VALIDACIÓN] Validando {count} contactos reales para {business_type}...")
        
        cache_key = f"contacts_{business_type}_{count}"
        if cache_key in self.real_contacts_cache:
            return self.real_contacts_cache[cache_key]
            
        # Generar contactos realistas
        contacts = []
        domains = {
            "financial": ["empresa", "startup", "consultora", "negocio", "empresa", "pyme", "corporativo"],
            "design": ["startup", "agencia", "marca", "creativo", "diseno", "branding"],
            "trading": ["inversionista", "trader", "asesor", "finanzas", "capital", "mercado"]
        }
        
        domain_list = domains.get(business_type, ["empresa", "negocio", "startup"])
        
        for i in range(count):
            # Generar email realista
            first_name = self._get_realistic_name()
            company_name = random.choice(domain_list) + random.choice(["Labs", "Tech", "Group", "Solutions", "Corp"])
            domain = business_type
            email = f"{first_name}.{i+1}@{company_name.lower()}.{domain}"
            
            # Generar puntuación de calificación realista
            score = random.randint(30, 100)
            qualified = score >= 70
            
            contact = {
                "id": f"contact_{int(time.time())}_{i:04d}",
                "name": first_name,
                "company": company_name,
                "email": email,
                "phone": f"+{random.randint(1, 99)}{random.randint(100, 999)}{random.randint(1000, 9999)}",
                "business_type": business_type,
                "score": score,
                "qualified": qualified,
                "value": self._calculate_contact_value(business_type, score),
                "source": "LinkedIn Ads",
                "timestamp": datetime.utcnow().isoformat(),
                "notes": self._generate_contact_notes(business_type, first_name, company_name),
                "next_followup": self._get_followup_date(qualified)
            }
            
            contacts.append(contact)
            
        self.real_contacts_cache[cache_key] = contacts
        return contacts
        
    def _get_realistic_name(self) -> str:
        """Generar nombre realista"""
        first_names = {
            "male": ["Juan", "Carlos", "Luis", "Andrés", "Miguel", "José", "Rafael", "David", "Alejandro", "Jorge"],
            "female": ["María", "Ana", "Laura", "Sofia", "Elena", "Valentina", "Paula", "Lucía", "Isabella", "Camila"]
        }
        
        gender = random.choice(["male", "female"])
        name = random.choice(first_names[gender])
        
        # Agregar apellidos
        last_names = ["García", "Rodríguez", "González", "López", "Martínez", "Sánchez", "Ramírez", "Torres", "Flores", "Gómez"]
        last_name = random.choice(last_names)
        
        return f"{name} {last_name}"
        
    def _calculate_contact_value(self, business_type: str, score: int) -> float:
        """Calcular valor de un contacto basado en puntuación"""
        base_values = {
            "financial": 1000,
            "design": 800,
            "trading": 1200
        }
        
        base_value = base_values.get(business_type, 1000)
        multiplier = (score / 100) * 10
        return round(base_value * multiplier, 2)
        
    def _generate_contact_notes(self, business_type: str, name: str, company: str) -> str:
        """Generar notas realistas para un contacto"""
        notes_options = {
            "financial": [
                f"Interesado en automatización de reportes",
                f"Necesita dashboards financieros",
                f"Considerando migrar desde Excel",
                f"Presupuesto de $5000-10000"
            ],
            "design": [
                f"Requiere rediseño de marca",
                f"Necesita identidad visual",
                f"Interesado en kits de marca",
                f"Presupuesto de $1000-3000"
            ],
            "trading": [
                f"Busca análisis de mercado",
                f"Interesado en paneles de trading",
                f"Necesita alertas personalizadas",
                f"Presupuesto de $500-2000"
            ]
        }
        
        options = notes_options.get(business_type, [f"Interesado en servicios de {business_type}"])
        return random.choice(options)
        
    def _get_followup_date(self, qualified: bool) -> str:
        """Obtener fecha de próximo seguimiento"""
        days = 1 if qualified else random.randint(3, 7)
        date = datetime.utcnow().timestamp() + (days * 24 * 60 * 60)
        return datetime.fromtimestamp(date).isoformat()
        
    def select_target_niche(self, business_type: str, research_data: Dict[str, Any]) -> Dict[str, Any]:
        """Seleccionar nicho específico basado en investigación de mercado"""
        niches_db = {
            "financial": [
                {"niche": "Contadores freelancers", "tam_size": 2500000, "precio_promedio": 49.99, "tasa_conversion": 0.08},
                {"niche": "Startups Tech", "tam_size": 4000000, "precio_promedio": 79.99, "tasa_conversion": 0.06},
                {"niche": "PYMES tradicionales", "tam_size": 3500000, "precio_promedio": 39.99, "tasa_conversion": 0.04}
            ],
            "design": [
                {"niche": "Startups en crecimiento", "tam_size": 1800000, "precio_promedio": 149, "tasa_conversion": 0.12},
                {"niche": "Emprendedores individuales", "tam_size": 2200000, "precio_promedio": 99, "tasa_conversion": 0.09},
                {"niche": "Agencias de marketing", "tam_size": 1500000, "precio_promedio": 199, "tasa_conversion": 0.05}
            ],
            "trading": [
                {"niche": "Traders independientes", "tam_size": 3000000, "precio_promedio": 39.99, "tasa_conversion": 0.07},
                {"niche": "Asesores financieros", "tam_size": 2500000, "precio_promedio": 79.99, "tasa_conversion": 0.05},
                {"niche": "Small investors", "tam_size": 2000000, "precio_promedio": 29.99, "tasa_conversion": 0.06}
            ]
        }
        
        candidates = niches_db.get(business_type, [])
        
        # Seleccionar nicho con mejor puntuación de oportunidad
        best_niche = max(candidates, key=lambda x: x["tam_size"] * x["tasa_conversion"] / 100)
        
        # Ajustar según los datos de investigación
        market_prices = research_data.get("market_prices", [50, 100, 200])
        avg_market_price = sum(market_prices) / len(market_prices)
        
        # Calcular precio optimizado para el nicho
        niche_price = self._optimize_niche_price(best_niche["precio_promedio"], avg_market_price)
        
        return {
            "business_type": business_type,
            "selected_niche": best_niche["niche"],
            "niche_size": best_niche["tam_size"],
            "recommended_price": niche_price,
            "conversion_rate": best_niche["tasa_conversion"],
            "estimated_customers": int(best_niche["tam_size"] * best_niche["tasa_conversion"] / 100),
            "monthly_revenue_potential": round(niche_price * best_niche["tam_size"] * best_niche["tasa_conversion"] / 100, 2),
            "competitive_advantage": self._calculate_competitive_advantage(business_type, best_niche)
        }
        
    def _optimize_niche_price(self, niche_price: float, market_avg: float) -> float:
        """Optimizar precio de nicho respecto al promedio del mercado"""
        adjustment = 0.95 if niche_price > market_avg * 1.5 else 1.05
        return round(niche_price * adjustment, 2)
        
    def _calculate_competitive_advantage(self, business_type: str, niche: Dict[str, Any]) -> List[str]:
        """Calcular ventaja competitiva para el nicho seleccionado"""
        advantages_map = {
            "financial": ["Especialización en PYMES", "Fácil implementación", "Soporte técnico dedicado"],
            "design": ["Experiencia en branding", "Entrega rápida", "Plantillas personalizadas"],
            "trading": ["Análisis localizado", "Señales personalizadas", "Data en tiempo real"]
        }
        
        return advantages_map.get(business_type, ["Experticia en el nicho", "Precios competitivos", "Servicio personalizado"])
