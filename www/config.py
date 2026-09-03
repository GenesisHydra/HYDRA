# HYDRA Corporate Email Configuration
# Este archivo contiene la configuración técnica para el sistema de correo corporativo.
# Para activarlo, simplemente añada su dominio y credenciales al servicio SMTP elegido
# (SendGrid, Mailgun, Postmark, o su propio servidor SMTP).

# Dominio base de HYDRA
HYDRA_DOMAIN = "hydra.business"

# Configuración SMTP (ejemplo con SendGrid - gratuito hasta 100 emails/día)
EMAIL_CONFIG = {
    "smtp_host": "smtp.sendgrid.net",
    "smtp_port": 587,
    "smtp_use_tls": True,
    "smtp_user": "apikey",  # Username para SendGrid
    "smtp_password": "SG.YourSendGridKey",  # API Key de SendGrid
    "from_email": "no-reply@hydra.business",
    
    # Todas las direcciones corporativas configuradas
    "corporate_emails": {
        "hello": "hello@hydra.business",
        "contact": "contact@hydra.business",
        "support": "support@hydra.business",
        "billing": "billing@hydra.business",
        "legal": "legal@hydra.business",
        "noreply": "noreply@hydra.business",
        "newsletter": "newsletter@hydra.business"
    },
    
    # Plantillas de email automatizadas
    "email_templates": {
        "welcome": {
            "subject": "¡Bienvenido a la comunidad HYDRA!",
            "body": "¡Bienvenido! Recibe mensualmente insights de automatización empresarial, estudios de caso y actualizaciones de producto."
        },
        "contact_received": {
            "subject": "Hemos recibido tu mensaje",
            "body": "Hemos recibido tu mensaje y te responderemos en un plazo de 24 horas."
        },
        "newsletter_welcome": {
            "subject": "Bienvenido al newsletter HYDRA",
            "body": "Gracias por suscribirte al newsletter mensual de HYDRA. Aquí encontrarás consejos de automatización, casos de estudio y actualizaciones de producto."
        }
    }
}

# Configuración de redes sociales preparada (usernames y biografías)
# Estas pueden crearse automáticamente o reclamarlas en las plataformas
SOCIAL_PROFILES = {
    "github": {
        "username": "GenesisHydra",
        "profile_url": "https://github.com/GenesisHydra",
        "bio": "HYDRA Business Automation Platform - Transformando PYMES con automatización inteligente de tesorería, pagos y operaciones open source.",
        "action_required": "Crear organización GitHub o solicitar invitación"
    },
    "linkedin": {
        "username": "Hydra Business",
        "profile_url": "https://linkedin.com/company/hydra-business",
        "bio": "HYDRA Business Automation Platform | Empoderando a PYMES con automatización financiera, CRM y treasury management | Open source business platform",
        "action_required": "Crear página de empresa LinkedIn"
    },
    "x_twitter": {
        "username": "@Hydra_Business",
        "profile_url": "https://x.com/GenesisHydra",
        "bio": "HYDRA Business Automation • Finanzas automatizadas • Dashboard en tiempo real • Stripe payments • #Automation #FinTech #PYMES",
        "action_required": "Crear cuenta verificada X"
    },
    "facebook": {
        "username": "Hydra Business",
        "profile_url": "https://facebook.com/GenesisHydra",
        "bio": "HYDRA Business Automation Platform | Automatización financiera para PYMES | Dashboard en vivo | Integración Stripe | Únete a nuestra comunidad",
        "action_required": "Crear página de Facebook"
    },
    "instagram": {
        "username": "@hydra.business",
        "profile_url": "https://instagram.com/hydra.business",
        "bio": "#GenesisHydra #Automation #FinTech • Transformando PYMES con automatización • Enlace en bio: hidra.business",
        "action_required": "Crear cuenta Instagram"
    },
    "youtube": {
        "username": "@GenesisHydra",
        "profile_url": "https://youtube.com/@GenesisHydra",
        "bio": "HYDRA Business Automation Tutorials | Tutoriales de treasury management | Stripe integration guides | Suscribite para nueva semanal",
        "action_required": "Crear canal de YouTube"
    },
    "tiktok": {
        "username": "@hydra.business",
        "profile_url": "https://tiktok.com/@hydra.business",
        "bio": "Transformando PYMES con automatización 🚀 #GenesisHydra #FinTech #BusinessAutomation",
        "action_required": "Crear cuenta TikTok"
    },
    "discord": {
        "username": "Hydra Business",
        "profile_url": "https://discord.gg/hydra",
        "bio": "HYDRA Community | Discusión sobre treasury management | Stripe integration help | Automación de negocios PYMES | Bienvenido a nuevos miembros!",
        "action_required": "Crear servidor Discord"
    },
    "telegram": {
        "username": "@GenesisHydra",
        "profile_url": "https://t.me/hydra_business",
        "bio": "HYDRA Business Automation - Actualizaciones semanales de treasury, tips de Stripe, casos de éxito PYMES | Canal no comercial",
        "action_required": "Crear canal de Telegram (pending bot token)"
    },
    "reddit": {
        "username": "u/GenesisHydra",
        "profile_url": "https://reddit.com/r/GenesisHydra",
        "bio": "r/GenesisHydra: Discussion, tips, and success stories about business automation, treasury management, and Stripe integration for SMEs",
        "action_required": "Crear subreddit (requiere karma/edad de cuenta)"
    }
}

# Biografías preparadas para cada plataforma
SOCIAL_BIOs = {
    "linkedin": "HYDRA Business Automation Platform | Empoderando a PYMES con automatización financiera, CRM y treasury management | Open source business platform",
    "x_twitter": "HYDRA Business Automation • Finanzas automatizadas • Dashboard en tiempo real • Stripe payments • #Automation #FinTech #PYMES",
    "instagram": "#GenesisHydra #Automation #FinTech • Transformando PYMES con automatización • Enlace en bio: hidra.business",
    "youtube": "HYDRA Business Automation Tutorials | Tutoriales de treasury management | Stripe integration guides | Suscribite para nueva semanal",
    "tiktok": "Transformando PYMES con automatización 🚀 #GenesisHydra #FinTech #BusinessAutomation",
    "discord": "HYDRA Community | Discusión sobre treasury management | Stripe integration help | Automación de negocios PYMES | Bienvenido a nuevos miembros!",
    "reddit": "r/GenesisHydra: Discussion, tips, and success stories about business automation, treasury management, and Stripe integration for SMEs"
}

# Banners y elementos visuales preparados (rutas relativas)
BANNERS = {
    "hero": "/static/banners/hero.svg",
    "logo": "/static/img/logo-hydra.svg",
    "favicon": "/favicon.ico"
}

# Planes del servicio (para páginas de pricing)
PLANS = {
    "financial": [
        {"name": "Starter", "price": "$29/mes", "features": ["Automated reports basic", "Email support", "Email delivery", "100 contacts"]},
        {"name": "Professional", "price": "$49/mes", "features": ["Automated reports advanced", "Priority support", "API access", "Unlimited contacts", "Custom dashboard"]},
        {"name": "Enterprise", "price": "Personalizado", "features": ["Dedicated account manager", "Custom integrations", "SLA guaranteed", "White label", "On-premise option"]}
    ],
    "design": [
        {"name": "Basic", "price": "$39/mes", "features": ["Logo profesional", "Tarjeta de presentación"]},
        {"name": "Professional", "price": "$69/mes", "features": ["Brand kit", "Social media templates", "Style guide"]},
        {"name": "Enterprise", "price": "Personalizado", "features": ["Dedicated designer", "Custom illustrations", "Priority support"]}
    ],
    "trading": [
        {"name": "Basic", "price": "$29/mes", "features": ["Gráficos de acciones", "Indicadores clave"]},
        {"name": "Professional", "price": "$59/mes", "features": ["Alertas automáticas", "Reportes mensuales", "API access"]},
        {"name": "Enterprise", "price": "Personalizado", "features": ["Dedicated analyst", "Custom strategies", "SLA guaranteed", "On-premise option"]}
    ]
}

# Social media post templates by platform
POST_TEMPLATES = {
    "linkedin": {
        "format": "Texto largo con párrafos, hashtags al final",
        "optimal_length": "1300 caracteres",
        "hashtags": ["#GenesisHydra", "#Automation", "#FinTech", "#PYMES"],
        "cta_include": True
    },
    "x_twitter": {
        "format": "Hilo o texto corto",
        "optimal_length": "280 caracteres",
        "hashtags": ["#GenesisHydra", "#Automation", "#FinTech"],
        "cta_include": True
    },
    "instagram": {
        "format": "Carrusel o foto única con leyenda",
        "optimal_length": "2,200 caracteres",
        "hashtags": ["#GenesisHydra", "#Automation", "#FinTech"],
        "cta_include": True
    },
    "facebook": {
        "format": "Publicación larga con imagen",
        "optimal_length": "Varía, max 63,206 caracteres",
        "hashtags": ["#GenesisHydra", "#Automation", "#FinTech"],
        "cta_include": True
    }
}

# CTE (Call to Action) templates para cada etapa del funnel
CTA_TEMPLATES = {
    "landing_primary": "Solicitar información",
    "landing_secondary": "Conocer planes",
    "contact_form_submit": "Mensaje enviado",
    "newsletter_signup": "Suscribirse",
    "download_trial": "Probar gratis",
    "social_post": "Visitar web",
    "email_cta": "Hola@hydra.business"
}