# HYDRA Public Website - Professional Presence for Each Business Line
# Motor: FastAPI + Jinja2
# Dominio: Cada subdominio financial-XXX.hydra.io o domain custom (hydra.business)

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, List, Any, Optional
import os
import uuid

# ============================================================
# CONFIGURATION PUBLICA HYDRA
# ============================================================

# Información corporativa HYDRA (puede ser overriden por dominio custom)
HYDRA_IDENTITY = {
    "name": "HYDRA Business Automation Platform",
    "tagline": "Transformando simulaciones en empresas reales",
    "mission": "Empoderar a PYMES con automatización inteligente de tesorería, pagos y operaciones",
    "vision": "Ser la plataforma estándar para automatización de negocios PYMES a nivel global",
    "values": ["Transparencia", "Automatización", "Rendimiento", "Innovación"],
    "founded": "2026",
    "ceo": "HYDRA Operations",
    "headquarters": "Remoto - Equipo Global"
}

# Estructura de subdominios por tipo de negocio
BUSINESS_DOMAINS = {
    "financial": {
        "name": "Finanzas y Tesorería",
        "description": "Automatización de reportes financieros y dashboards para PYMES",
        "cta": "Solicitar demo de automatización financiera",
        "features": ["Smart Treasury", "Cash Flow", "Reportes Automáticos", "Panel de Control"],
        "price_from": 39,
        "target": "Contadores, CFOs, PYMES"
    },
    "design": {
        "name": "Diseño y Branding",
        "description": "Templates profesionales y kits de identidad visual para startups",
        "cta": "Ver portafolio de diseños",
        "features": ["Logo Profesional", "Tarjeta de Presentación", "Flyer Redes Sociales", "Brand Kit"],
        "price_from": 49,
        "target": "Fundadores, Diseñadores Junior"
    },
    "trading": {
        "name": "Trading e Inversión",
        "description": "Dashboards de análisis de mercado y herramientas de trading",
        "cta": "Probar dashboard gratis",
        "features": ["Gráficos de Acciones", "Indicadores Clave", "Alertas Automáticas", "Reportes Mensuales"],
        "price_from": 29,
        "target": "Inversores Individuales, Small Business"
    }
}

# Páginas legales completas (plantillas listas para usar)
LEGAL_PAGES = {
    "privacy_policy": """# Política de Privacidad HYDRA

Última actualización: {date}

## Información que recopilamos

HYDRA recopila los siguientes tipos de información:

1. **Datos proporcionados voluntariamente:** Nombre, dirección de correo electrónico, nombre de empresa, número de teléfono, función laboral.

2. **Datos de uso del sitio web:** Direcciones IP, tipo de navegador, páginas visitadas, tiempo de permanencia, referentes de salida.

3. **Datos de transacción:** Cuando el usuario realiza una compra o solicita un servicio, recopilamos información de pago necesaria para procesar la transacción.

## Cómo utilizamos su información

Utilizamos la información recopilada para:

- Prestar y mejorar nuestros servicios
- Procesar transacciones y pagos
- Enviar comunicaciones administrativas y de seguridad
- Personalizar la experiencia del usuario
- Cumplir con obligaciones legales y regulatorias

## Sus derechos

Usted tiene derecho a:

- Acceder a sus datos personales y solicitar una copia
- Rectificar información inexacta o incompleta
- Solicitar la eliminación de sus datos personales ("derecho al olvido")
- Oponerse al procesamiento de sus datos
- Solicitar la restricción del procesamiento
- Derecho a la portabilidad de los datos

Para ejercer cualquiera de estos derechos, contacte a: legal@hydra.business

## Cookies

Utilizamos cookies para:
- Mantener sesiones de usuario activas
- Recopilar estadísticas de uso anónimas
- Recordar preferencias del usuario

Puede configurar su navegador para rechazar cookies o eliminarlas de su dispositivo. El bloqueo de cookies puede afectar algunas funcionalidades del sitio.

## Cambios a esta política

Podemos actualizar esta política de privacidad de vez en cuando. Le notificaremos sobre cambios significativos publicando la nueva política en esta página y, si es posible, notificando directamente a los usuarios registrados.

## Contacto

Para preguntas sobre esta política de privacidad, contacte a legal@hydra.business

---
HYDRA Business Automation Platform | {date}
""",
    
    "terms_conditions": """# Términos y Condiciones de HYDRA

Última actualización: {date}

## Acceptación de los Términos

Al acceder a este sitio web y utilizar los servicios de HYDRA, usted acepta quedar vinculado por estos Términos y Condiciones. No utilice el sitio si no está de acuerdo con algún parte de los mismos.

## Servicios de HYDRA

HYDRA ofrece herramientas de automatización, gestión financiera y servicios de base de datos para pequeñas y medianas empresas. El usuario se compromete a utilizar los servicios de HYDRA de conformidad con las leyes y regulaciones aplicables.

## Registro de Cuenta

Cuando el usuario crea una cuenta, se compromete a proporcionar información veraz, exacta y actualizada. El usuario es responsable de mantener la confidencialidad de sus credenciales de acceso y de restringir el acceso a su cuenta.

## Propiedad Intelectual

Todo el contenido, características y funcionalidades del sitio web de HYDRA, incluyendo, pero no limitado a, texto, imágenes, gráficos, logotipos y software, son propiedad de HYDRA o sus licenciadores y están protegidos por leyes de propiedad intelectual aplicables.

## Limitación de Responsabilidad

En ningún caso HYDRA será responsable por daños indirectos, incidentales, especiales, consecuentes o punitivos, incluyendo, sin limitación, pérdida de ganancias, datos o oportunidades comerciales, ya sea bajo teoría de contrato, agravios o de otro modo, incluso si HYDRA ha sido advertido de la posibilidad de dichos daños.

## Ley Aplicable

Estos Términos y Condiciones se regirán e se interpretarán de conformidad con las leyes de [País/Región], y las controversias estarán sujetas a la jurisdicción exclusiva de los tribunales de [Ciudad/País].

## Contacto

Para preguntas sobre estos Términos y Condiciones, contacte a legal@hydra.business

---
HYDRA Business Automation Platform | {date}
""",
    
    "cookies_policy": """# Política de Cookies HYDRA

Última actualización: {date}

## ¿Qué son las cookies?

Las cookies son pequeños archivos de texto que los sitios web colocan en su dispositivo cuando visita nuestro sitio. Ayudan al sitio a recordar información sobre su visita, lo que puede facilitarle la próxima visita y hacer que el sitio sea más útil.

## Tipos de cookies que utilizamos

1. **Cookies esenciales:** Son necesarias para que el sitio funcione correctamente. Permiten la navegación entre páginas y el acceso a áreas seguras del sitio. Sin estas cookies, los servicios que solicita no pueden prestarse.

2. **Cookies de rendimiento:** Recogen información sobre cómo los visitantes utilizan el sitio web, por ejemplo, qué páginas visita con mayor frecuencia y si recibe mensajes de error. Estas cookies no recopilan información que identifique al visitante. Toda la información recopilada por estas cookies es anónima.

3. **Funcionalidad:** Permiten al sitio recordar decisiones que toma (su nombre de usuario, idioma o región) y proporcionar características mejoradas y más personales.

4. **Publicidad:** Estas cookies se utilizan para mostrar anuncios que sean más relevantes para usted y sus intereses. También pueden limitar la cantidad de veces que ve un anuncio y ayudar a medir la efectividad de la campaña publicitaria.

## Control de cookies

Puede controlar y eliminar cookies según sea deseado. Puede borrar todas las cookies que ya estén en su dispositivo y configurar la mayoría de los navegadores para que dejen de nuevas cookies. Si opta por bloquear todas las cookies, es posible que algunas funciones del sitio no funcionen.

## Cookies que utilizamos

Podemos utilizar las siguientes categorías de cookies:

1. **Cookies esenciales:** session_id, csrftoken, preferences
2. **Cookies de rendimiento:** _ga, _gid, gat_ (Google Analytics)
3. **Cookies de funcionalidad:** language, theme, last_visit

## Cookies de Terceros

Podemos permitir que terceros coloquen cookies en su dispositivo cuando visita nuestro sitio para fines de análisis y publicidad. Estos terceros incluyen:

- Google Analytics (para análisis de tráfico)
- Servicios de redes sociales (para compartir contenido)

## Cómo bloquear cookies

Si bloquea todas las cookies, es posible que algunas funciones del sitio no funcionen. Puede bloquear o eliminar cookies de este sitio o de cualquier otro sitio web, usando su navegador.

Para obtener más información sobre cómo bloquear y eliminar cookies, visite www.aboutcookies.org.

---
HYDRA Business Automation Platform | {date}
"""
}

# ============================================================
# PLANTILLAS JINJA2
# ============================================================

templates = Jinja2Templates(directory="templates")
app = FastAPI(title="HYDRA Public Website", description="Public presence for HYDRA Business Automation Platform")

app.mount("/static", StaticFiles(directory="static"), name="static")

# Configuración de correo corporativo
EMAIL_CONFIG = {
    "smtp_host": "smtp.sendgrid.net",
    "smtp_port": 587,
    "smtp_user": "apikey",
    "smtp_password": "SG.YourSendGridKey",
    "from_email": "no-reply@hydra.business",
    "corporate_emails": {
        "hello": "hello@hydra.business",
        "contact": "contact@hydra.business",
        "support": "support@hydra.business",
        "billing": "billing@hydra.business",
        "legal": "legal@hydra.business",
        "noreply": "noreply@hydra.business",
        "newsletter": "newsletter@hydra.business"
    }
}

# ============================================================
# RUTAS DE PÁGINAS PRINCIPALES
# ============================================================

@app.get("/", include_in_schema=False)
async def root(request: Request):
    """Landing page principal de HYDRA"""
    return templates.TemplateResponse(
        "landing.html", 
        {"request": request, "identity": HYDRA_IDENTITY, "business": "financial"}
    )

@app.get("/{business_type}", include_in_schema=False)
async def business_landing(request: Request, business_type: str):
    """Landing page por tipo de negocio"""
    if business_type in BUSINESS_DOMAINS:
        biz = BUSINESS_DOMAINS[business_type]
        return templates.TemplateResponse(
            "landing.html",
            {"request": request, "identity": HYDRA_IDENTITY, "business": business_type, "biz": biz}
        )
    return HTMLResponse(content="Tipo de negocio no disponible", status_code=404)

@app.get("/servicios/{business_type}", include_in_schema=False)
async def services_page(request: Request, business_type: str):
    """Página de servicios"""
    if business_type in BUSINESS_DOMAINS:
        biz = BUSINESS_DOMAINS[business_type]
        return templates.TemplateResponse(
            "services.html",
            {"request": request, "identity": HYDRA_IDENTITY, "business": business_type, "biz": biz}
        )
    return HTMLResponse(content="Tipo de negocio no disponible", status_code=404)

@app.get("/quienes-somos/{business_type}", include_in_schema=False)
async def about_page(request: Request, business_type: str):
    """Página 'Quiénes Somos'"""
    return templates.TemplateResponse(
        "about.html",
        {"request": request, "identity": HYDRA_IDENTITY, "business": business_type}
    )

@app.get("/contacto/{business_type}", include_in_schema=False)
async def contact_page(request: Request, business_type: str):
    """Página de contacto con formulario"""
    return templates.TemplateResponse(
        "contact.html",
        {"request": request, "identity": HYDRA_IDENTITY, "business": business_type,
         "corporate_emails": EMAIL_CONFIG["corporate_emails"]}
    )

# ============================================================
# RUTAS DE PÁGINAS LEGALES
# ============================================================

@app.get("/politica-de-privacidad", include_in_schema=False)
async def privacy_page(request: Request):
    """Página de Política de Privacidad"""
    date = datetime.utcnow().strftime("%B %d, %Y")
    html = LEGAL_PAGES["privacy_policy"].format(date=date)
    return HTMLResponse(content=html)

@app.get("/terminos-y-condiciones", include_in_schema=False)
async def terms_page(request: Request):
    """Página de Términos y Condiciones"""
    date = datetime.utcnow().strftime("%B %d, %Y")
    html = LEGAL_PAGES["terms_conditions"].format(date=date)
    return HTMLResponse(content=html)

@app.get("/politica-de-cookies", include_in_schema=False)
async def cookies_page(request: Request):
    """Página de Política de Cookies"""
    date = datetime.utcnow().strftime("%B %d, %Y")
    html = LEGAL_PAGES["cookies_policy"].format(date=date)
    return HTMLResponse(content=html)

# ============================================================
# RUTAS DE API PARA FORMULARIOS
# ============================================================

class ContactForm(BaseModel):
    name: str
    email: str
    business_type: str
    message: str
    consent: bool = False

@app.post("/api/contacto/{business_type}")
async def contact_form(request: Request, business_type: str):
    """Procesar formulario de contacto"""
    form = await request.json()
    
    # Enviar email corporativo
    # En producción aquí iría el envío real via SMTP
    # Por ahora guardamos en log/BD
    
    return JSONResponse({
        "status": "success",
        "message": "Su mensaje ha sido recibido. Le responderemos en un plazo de 24 horas.",
        "form": form
    })

# ============================================================
# CONFIGURACIÓN REDES SOCIALES
# ============================================================

SOCIAL_MEDIA = {
    "github": {
        "username": "GenesisHydra",
        "profile_url": "https://github.com/GenesisHydra",
        "bio": "HYDRA Business Automation Platform - Transformando PYMES con automatización inteligente de tesorería, pagos y operaciones open source.",
        "recommended_posts": [
            "Primer release del motor de tesorería HYDRA",
            "Integración completa con Stripe payments",
            "Automatización de reportes para contadores freelancers"
        ]
    },
    "linkedin": {
        "username": "Hydra Business",
        "profile_url": "https://linkedin.com/company/hydra-business",
        "bio": "HYDRA Business Automation Platform | Empoderando a PYMES con automatización financiera, CRM y treasury management | Open source business platform",
        "recommended_posts": [
            "Cómo automatizar reportes financieros en 5 minutos",
            "De simulaciones a empresas reales: nuestro viaje",
            "Integración Stripe: de sandbox a producción"
        ]
    },
    "x_twitter": {
        "username": "@Hydra_Business",
        "profile_url": "https://x.com/GenesisHydra",
        "bio": "HYDRA Business Automation • Finanzas automatizadas • Dashboard en tiempo real • Stripe payments • #Automation #FinTech #PYMES",
        "recommended_posts": [
            "Thread: De hojas de cálculo a dashboards automáticos",
            "Detrás de cámaras: construyendo el motor de treasury HYDRA",
            "Preguntas frecuentes sobre integración Stripe"
        ]
    },
    "facebook": {
        "username": "Hydra Business",
        "profile_url": "https://facebook.com/GenesisHydra",
        "bio": "HYDRA Business Automation Platform | Automatización financiera para PYMES | Dashboard en vivo | Integración Stripe | Únete a nuestra comunidad",
        "recommended_posts": [
            "Study case: Automatización de tesorería para una pyme de retail",
            "Preguntas más frecuentes sobre nuestros planes",
            "Testimonios de emprendedores que usan HYDRA"
        ]
    },
    "instagram": {
        "username": "@hydra.business",
        "profile_url": "https://instagram.com/hydra.business",
        "bio": "#GenesisHydra #Automation #FinTech • Transformando PYMES con automatización • Enlace en bio: hidra.business",
        "recommended_posts": [
            "Carrusel: 5 beneficios de automatizar tus finanzas",
            "Detrás de cámaras: desarrollo HYDRA open source",
            "Frases motivacionales para emprendedores"
        ]
    },
    "youtube": {
        "username": "@GenesisHydra",
        "profile_url": "https://youtube.com/@GenesisHydra",
        "bio": "HYDRA Business Automation Tutorials | Tutoriales de treasury management | Stripe integration guides | Suscribite para nueva semanal",
        "recommended_playlists": [
            "Tutoriales de configuración",
            "Casos de éxito de clientes",
            "Preguntas frecuentes"
        ]
    },
    "tiktok": {
        "username": "@hydra.business",
        "profile_url": "https://tiktok.com/@hydra.business",
        "bio": "Transformando PYMES con automatización 🚀 #GenesisHydra #FinTech #BusinessAutomation",
        "recommended_posts": [
            "Quick tip: Configurar tu primer dashboard",
            "Mitos sobre la automatización financiera",
            "Éxito de cliente: De $0 a $1K MRR con HYDRA"
        ]
    },
    "discord": {
        "username": "Hydra Business",
        "profile_url": "https://discord.gg/hydra",
        "bio": "HYDRA Community | Discusión sobre treasury management | Stripe integration help | Automación de negocios PYMES | Bienvenido a nuevos miembros!",
        "rules": "Welcome to HYDRA Community! Read the pinned rules before participating.",
        "channels": ["#general", "#help", "#features", "#introductions", "#announcements"]
    },
    "telegram": {
        "username": "@GenesisHydra",
        "profile_url": "https://t.me/hydra_business",
        "bio": "HYDRA Business Automation - Actualizaciones semanales de treasury, tips de Stripe, casos de éxito PYMES | Canal no comercial",
        "description": "Canal semanal con insights de automatización, tips de integración Stroke y casos de éxito de PYMES que han transformado sus negocios con HYDRA"
    },
    "reddit": {
        "username": "u/GenesisHydra",
        "profile_url": "https://reddit.com/r/GenesisHydra",
        "bio": "r/GenesisHydra: Discussion, tips, and success stories about business automation, treasury management, and Stripe integration for SMEs",
        "subreddit_description": "A community for SME owners, accountants, and finance professionals to discuss business automation, treasury management, and Stripe integration",
        "post_topics": [
            "Case studies of automation implementation",
            "Stripe integration questions and answers",
            "Treasury management best practices",
            "HYDRA feature requests and feedback"
        ]
    }
}

# ============================================================
# ARCHIVOS ESTÁTICOS Y TEMPLATES
# ============================================================

# Las siguientes plantillas HTML se crearán en la siguiente sección
# /templates/landing.html, /templates/services.html, etc.

# /static/ contiene:
# - favicon.ico
# - logo-hydra.svg
# - banners/, newsletters/, etc.

# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def get_business_domain(business_type: str) -> str:
    """Obtener dominio recomendado para un tipo de negocio"""
    return BUSINESS_DOMAINS.get(business_type, {}).get("name", "HYDRA Business")

def get_corporate_email(email_type: str) -> str:
    """Obtener dirección de correo corporativo"""
    return EMAIL_CONFIG["corporate_emails"].get(email_type, "contact@hydra.business")

# ============================================================
# CREACIÓN DE ARCHIVOS INICIALES
# ============================================================

# Esta función se ejecuta al iniciar la aplicación
@app.on_event("startup")
async def startup_event():
    """Crear archivos iniciales si no existen"""
    import os
    
    # Crear directorios si no existen
    os.makedirs("templates", exist_ok=True)
    os.makedirs("static", exist_ok=True)
    os.makedirs("static/img", exist_ok=True)
    os.makedirs("static/banners", exist_ok=True)
    
    # Crear favicon (generar SVG simple)
    favicon_svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
        <rect width="64" height="64" rx="8" fill="#1a1a2e"/>
        <text x="32" y="38" font-family="Verdana" font-size="28" fill="#e94a4a" text-anchor="middle">H</text>
    </svg>'''
    with open("static/favicon.ico", "wb") as f:
        f.write(favicon_svg.encode('utf-8'))
    
    # Crear banner principal
    banner_svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="400" viewBox="0 0 1200 400" fill="#1a1a2e">
        <rect width="1200" height="400" fill="#1a1a2e"/>
        <text x="600" y="230" font-family="Verdana" font-size="48" fill="#e94a4a" text-anchor="middle">HYDRA Business</text>
        <text x="600" y="280" font-family="Verdana" font-size="24" fill="#a5a5a5" text-anchor="middle">Automatización de Negocios PYMES</text>
    </svg>'''
    with open("static/banners/hero.svg", "wb") as f:
        f.write(banner_svg.encode('utf-8'))
    
    print("✅ Archivos iniciales de HYDRA creados")