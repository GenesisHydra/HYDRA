# GenesisHydra

**GenesisHydra** es una plataforma de código abierto para la automatización de negocios PYMES. Transformamos simulaciones en empresas reales con herramientas de gestión financiera, integración de pagos (Stripe), treasury management y marketing automatizado.

## 🚀 Sobre Nosotros

GenesisHydra empodera a pequeñas y medianas empresas con automatización inteligente para:
- Gestión automática de tesorería y flujos de efectivo
- Procesamiento de pagos mediante Stripe
- Reportes y dashboards en tiempo real
- Captura y conversión de leads
- Marketing y content automation

## 📦 Características Principales

| Característica | Descripción |
|---------------|-------------|
| **Treasury Management** | Gestión automática de flujos de efectivo, presupuestos y reportes financieros |
| **Stripe Integration** | Procesamiento de pagos seguro con Stripe Connect |
| **CRM y Lead Tracking** | Captura, calificación y seguimiento de leads |
| **Market Research** | Análisis TAM/SAM/SOM, competencia y precios de mercado |
| **Content Marketing** | Blog automatizado, redes sociales, newsletter |
| **Accounting** | Reportes contables y métricas de desempeño |

## 🌐 Web Corporativa

La web pública de GenesisHydra está desplegada en GitHub Pages y incluye:

- Landing page principal con descripción de servicios
- Páginas por tipo de negocio (financial, design, trading)
- Páginas legales (privacy policy, terms & conditions, cookies policy)
- Formulario de contacto con envío de email
- Sección de pricing/planos
- Sección "Quiénes Somos"

Accede a la web pública en: `https://GenesisHydra.github.io`

## 📋 Estructura del Repositorio

```
GenesisHydra/
├── .github/            # GitHub Actions workflows
├── docs/               # Documentación operativa
├── src/                # Código fuente Python
├── www/                # Sitio web estático (GitHub Pages)
│   ├── templates/      # Plantillas HTML (Jinja2)
│   ├── static/         # CSS, images, favicons
│   └── main.py         # Aplicación FastAPI entry point
├── data/               # Datos de negocio y reports
├── requirements.txt    # Dependencias Python
├── gunicorn.conf.py    # Configuración del servidor
└── README.md           # Este archivo
```

## 🛠️ Tecnologías Utilizadas

- **FastAPI**: Framework web Python de alto rendimiento
- **Jinja2**: Motor de plantillas HTML
- **SQLAlchemy**: ORM para base de datos (SQLite → PostgreSQL)
- **Stripe API**: Procesamiento de pagos
- **SendGrid**: Servicio de correo transaccional
- **GitHub Pages**: Despliegue web estático
- **Git**: Control de versiones

## 🚀 Despliegue Automático

El sitio web se despliega automáticamente en GitHub Pages mediante cada push al rama `main`.

El flujo de trabajo (`/.github/workflows/deploy.yml`):
1. Detecta cambios en los archivos `www/` (templates HTML, static assets)
2. Construye el sitio estático
3. Despliega a `https://GenesisHydra.github.io`

## 🔧 Despliegue Local

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar localmente
uvicorn main:app --host 0.0.0.0 --port 8000

# Acceder en: http://localhost:8000
```

## 📦 Personalizar Dominio

Para conectar un dominio personalizado:

1. En el reposorio GitHub, ve a **Settings > Pages**
2. Selecciona "Custom domain" y escribe tu dominio
3. Configura los registros DNS CNAME según las instrucciones de GitHub
4. Actualiza `HYDRA_DOMAIN` en `www/config.py`

## 📧 Contacto

- **Email corporativo**: `contact@genesishydra.com`
- **Soporte**: Abre un issue en el repositorio de GitHub
- **Comunidad**: Únete a la discusión en `r/GenesisHydra`

---

*GenesisHydra - Transformando simulaciones en empresas reales desde 2026*
