# SEO Optimizer - Search Engine Optimization for HYDRA landing pages

import re
from datetime import datetime
from typing import Dict, List, Any, Optional


class SEOOptimizer:
    def __init__(self, focus_keyword: str, business_type: str):
        self.focus_keyword = focus_keyword
        self.business_type = business_type
        self.meta_tags: Dict[str, str] = {}
        self.schema_data: Dict[str, Any] = {}

    def optimize_title(self, title: str, max_length: int = 60) -> str:
        """Optimizar título para SEO"""
        # Truncar a longitud máxima
        truncated = title[:max_length-3] + "..." if len(title) > max_length else title

        # Añadir marca si caben caracteres adicionales
        brand_suffix = " | Hydra Business"
        if len(truncated) + len(brand_suffix) <= max_length:
            truncated += brand_suffix

        return truncated

    def generate_meta_tags(self, title: str, description: str = "") -> Dict[str, str]:
        """Generar etiquetas meta completas"""
        # Generar descripción si no existe o está vacía
        if not description:
            description = self._generate_description(title)

        # Limitar descripción a 160 caracteres
        desc_limit = 160
        description = description[:desc_limit-3] + "..." if len(description) > desc_limit else description

        self.meta_tags = {
            "title": self.optimize_title(title),
            "description": description,
            "keywords": self.focus_keyword,
            "robots": "index, follow",
            "author": "Hydra Business",
            "viewport": "width=device-width, initial-scale=1.0"
        }
        return self.meta_tags

    def _generate_description(self, title: str) -> str:
        """Generar descripción automática basada en el título"""
        templates = {
            "financial": f"Automatización de reportes y dashboards para {self.focus_keyword}. Optimiza tu gestión financiera con Hydra Business.",
            "design": f"Templates y kits de marca profesionales para {self.focus_keyword}. Eleva tu identidad visual con Hydra Business.",
            "trading": f"Análisis de mercado y dashboards de trading para {self.focus_keyword}. Toma decisiones informadas con Hydra Business."
        }

        return templates.get(self.business_type, f"Soluciones empresariales automatizadas para {self.focus_keyword}.")

    def generate_schema_markup(self, page_type: str = "Website") -> Dict[str, Any]:
        """Generar datos estructurados Schema.org"""
        schema: Dict[str, Any] = {
            "@context": "https://schema.org",
            "@type": page_type,
            "name": self.meta_tags.get("title", "Hydra Business"),
            "description": self.meta_tags.get("description"),
            "author": {
                "@type": "Organization",
                "name": "Hydra Business"
            },
            "dateCreated": datetime.utcnow().isoformat() + "Z",
            "dateModified": datetime.utcnow().isoformat() + "Z"
        }

        self.schema_data = schema
        return schema

    def get_seo_score_guidelines(self) -> Dict[str, Any]:
        """Obtener directrices para puntuación SEO"""
        return {
            "title_length": {
                "optimal": "50-60 caracteres",
                "current": f"{len(self.meta_tags.get('title', ''))} caracteres",
                "status": "optimal" if 50 <= len(self.meta_tags.get('title', '')) <= 60 else "needs_improvement"
            },
            "description_length": {
                "optimal": "150-160 caracteres",
                "current": f"{len(self.meta_tags.get('description', ''))} caracteres",
                "status": "optimal" if 150 <= len(self.meta_tags.get('description', '')) <= 160 else "needs_improvement"
            },
            "focus_keyword_usage": {
                "in_title": self.focus_keyword.lower() in self.meta_tags.get("title", "").lower(),
                "in_description": self.focus_keyword.lower() in self.meta_tags.get("description", "").lower(),
                "status": "complete" if (self.focus_keyword.lower() in self.meta_tags.get("title", "").lower() and
                                       self.focus_keyword.lower() in self.meta_tags.get("description", "").lower()) else "partial"
            }
        }


# Factory function para crear optimizador SEO
def create_seo_optimizer(focus_keyword: str, business_type: str) -> SEOOptimizer:
    return SEOOptimizer(focus_keyword, business_type)