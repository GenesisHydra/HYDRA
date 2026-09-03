# Content Marketing Agent - Automated Content Pipeline for HYDRA

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from database import SessionLocal, BusinessModel, LeadModel, CampaignModel


class ContentMarketingAgent:
    def __init__(self, business_type: str, session: Optional[SessionLocal] = None):
        self.business_type = business_type
        self.session = session or SessionLocal()
        self.business = self.session.query(BusinessModel).filter(
            BusinessModel.business_type == business_type
        ).first()
        if not self.business:
            raise ValueError(f"Business of type {business_type} not found in database")
    
    def generate_blog_post(self, topic: str, target_keyword: str) -> Dict[str, Any]:
        """Generar entrada de blog optimizada para SEO"""
        # Obtener datos de investigación de mercado
        from hydra.controller.market_research import MarketResearch
        mr = MarketResearch()
        research = mr.research_market(self.business_type, self.business.business_id)
        
        # Determinar formato basado en el tipo de negocio
        formats = {
            "financial": {
                "structure": [
                    {"heading": "Introducción", "h_level": 2},
                    {"heading": "Problemática actual", "h_level": 3},
                    {"heading": "Solución con automatización", "h_level": 3},
                    {"heading": "Beneficios clave", "h_level": 3},
                    {"heading": "Casos de uso", "h_level": 3},
                    {"heading": "Conclusión", "h_level": 2}
                ],
                "cta": "Solicitar demo gratuita",
                "cta_url": f"/demo-{self.business.business_id}"
            },
            "design": {
                "structure": [
                    {"heading": "Por qué tu marca necesita renovación", "h_level": 2},
                    {"heading": "Elementos clave de un buen diseño", "h_level": 3},
                    {"heading": "Plantillas vs. diseño custom", "h_level": 3},
                    {"heading": "Cómo Hydra puede ayudar", "h_level": 3},
                    {"heading": "Ejemplos de éxito", "h_level": 3},
                    {"heading": "Próximos pasos", "h_level": 2}
                ],
                "cta": "Ver portafolio",
                "cta_url": f"/portfolio-{self.business.business_id}"
            },
            "trading": {
                "structure": [
                    {"heading": "Análisis de mercado actual", "h_level": 2},
                    {"heading": "Señales de trading importantes", "h_level": 3},
                    {"heading": "Cómo la automatización mejora resultados", "h_level": 3},
                    {"heading": "Gestión de riesgos", "h_level": 3},
                    {"heading": "Herramientas recomendadas", "h_level": 3},
                    {"heading": "Conclusión", "h_level": 2}
                ],
                "cta": "Probar dashboard gratis",
                "cta_url": f"/dashboard-{self.business.business_id}"
            }
        }
        
        format_data = formats.get(self.business_type, formats["financial"])
        
        # Generar contenido estructurado
        content_parts = []
        for segment in format_data["structure"]:
            content_parts.append(f"<{segment['h_level']}>{segment['heading']}</{segment['h_level']}>")
        
        # Añadir CTA
        content_parts.append(f"<p><strong>{format_data['cta']}</strong>: <a href=\"{format_data['cta_url']}\">Aquí</a></p>")
        
        post = {
            "id": f"post-{uuid.uuid4().hex[:8]}",
            "topic": topic,
            "focus_keyword": target_keyword,
            "business_type": self.business_type,
            "business_id": self.business.business_id,
            "title": f"{topic}: Una guía para {self.business_type}",
            "meta_description": f"Descubre cómo {self.business_type} pueden beneficiarse de la automatización. {target_keyword} y más en esta guía completa.",
            "structure": format_data["structure"],
            "cta": format_data["cta"],
            "cta_url": format_data["cta_url"],
            "content_parts": content_parts,
            "estimated_read_time": max(3, len(topic.split()) // 200),
            "published_at": datetime.utcnow().isoformat(),
            "status": "draft",
            "tags": [target_keyword, self.business_type, "automation", "business"]
        }
        
        # Guardar en base de datos
        db_lead = LeadModel(
            lead_id=f"content_{post['id']}",
            business_id=self.business.business_id,
            email=f"content_{post['id']}@hydra.business",
            source="content_marketing",
            timestamp=datetime.utcnow(),
            qualified=False,
            score=80,
            value=self.business.pricing * 6
        )
        self.session.add(db_lead)
        self.session.commit()
        
        return post
    
    def generate_social_media_posts(self, count: int = 3) -> List[Dict[str, Any]]:
        """Generar publicaciones para redes sociales"""
        posts = []
        business_benefits = {
            "financial": "Automatiza tus reportes financieros en 5 minutos",
            "design": "Crea identidad visual profesional sin diseñador",
            "trading": "Analiza mercados con dashboards inteligentes"
        }
        
        benefit = business_benefits.get(self.business_type, "Automatiza tu negocio")
        
        for i in range(min(count, 5)):
            post = {
                "id": f"social_{uuid.uuid4().hex[:8]}",
                "platform": ["linkedin", "twitter", "facebook"][i % 3],
                "content": f"{benefit} #GenesisHydra #Automation #{self.business_type}",
                "hashtags": ["#GenesisHydra", "#Automation", f"#{self.business_type}"],
                "scheduled_at": (datetime.utcnow() + timedelta(minutes=i*15)).isoformat(),
                "status": "scheduled",
                "business_id": self.business.business_id
            }
            posts.append(post)
            
            # Guardar en base de datos
            db_campaign = CampaignModel(
                campaign_id=f"social_{post['id']}",
                business_id=self.business.business_id,
                platform=post["platform"],
                budget=0.0,
                leads_generated=0,
                cost_per_lead=0.0,
                status="pending"
            )
            self.session.add(db_campaign)
        
        self.session.commit()
        return posts
    
    def content_calendar(self, weeks: int = 4) -> Dict[str, Any]:
        """Generar calendario de contenido"""
        days = ["lunes", "martes", "miércoles", "jueves", "viernes"]
        calendar = {
            "business_type": self.business_type,
            "weeks": weeks,
            "schedule": []
        }
        
        topics_by_week = {
            "financial": [
                "Automatización de reportes mensuales",
                "Dashboards financieros en tiempo real",
                "Consejos fiscales para emprendedores",
                "ROI de la automatización empresarial"
            ],
            "design": [
                "Identidad de marca para startups",
                "Plantillas profesionales para redes sociales",
                "Guía de typography para no diseñadores",
                "Tendencias de diseño 2026"
            ],
            "trading": [
                "Análisis de tendencias de mercado",
                "Gestión de riesgos para traders",
                "Indicadores técnicos esenciales",
                "Cómo la tecnología mejora trading"
            ]
        }
        
        weekly_topics = topics_by_week.get(self.business_type, topics_by_week["financial"])
        
        for week in range(weeks):
            week_schedule = {
                "week": week + 1,
                "days": []
            }
            for day_idx, day in enumerate(days):
                topic_idx = (week * 5 + day_idx) % len(weekly_topics)
                topic = weekly_topics[topic_idx]
                
                day_entry = {
                    "day": day,
                    "topic": topic,
                    "content_type": "blog_post" if day_idx < 3 else "social_media",
                    "cta": "Contacto" if day_idx < 3 else "Suscripción"
                }
                week_schedule["days"].append(day_entry)
            
            calendar["schedule"].append(week_schedule)
        
        return calendar


# Factory function para crear agente de content marketing
def create_content_marketing_agent(business_type: str, session: Optional[SessionLocal] = None) -> ContentMarketingAgent:
    return ContentMarketingAgent(business_type, session)