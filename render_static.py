#!/usr/bin/env python3
"""
Render static HTML for GenesisHydra GitHub Pages site using direct Jinja2 rendering.
"""
import os
import shutil
from pathlib import Path

import main
from main import templates

# Use the Jinja2 environment from the FastAPI app
jinja_env = templates.env

# Output directory
OUTPUT_DIR = Path("_site")
if OUTPUT_DIR.exists():
    shutil.rmtree(OUTPUT_DIR)
OUTPUT_DIR.mkdir()

def render_template(template_name: str, context: dict) -> str:
    """Render a Jinja2 template with given context."""
    template = jinja_env.get_template(template_name)
    return template.render(**context)

def save_rendered(template_name: str, context: dict, output_path: Path):
    """Render template and save to output_path."""
    print(f"Rendering {template_name} -> {output_path}")
    html = render_template(template_name, context)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")

# 1. Root landing page (financial)
save_rendered(
    "landing.html",
    {
        "identity": main.HYDRA_IDENTITY,
        "business_type": "financial",
        "biz": main.BUSINESS_DOMAINS["financial"]
    },
    OUTPUT_DIR / "index.html"
)

# 2. Business type pages
for biz_type, biz_info in main.BUSINESS_DOMAINS.items():
    # Landing page for business type
    save_rendered(
        "landing.html",
        {
            "identity": main.HYDRA_IDENTITY,
            "business_type": biz_type,
            "biz": biz_info
        },
        OUTPUT_DIR / biz_type / "index.html"
    )
    # Services page
    save_rendered(
        "services.html",
        {
            "identity": main.HYDRA_IDENTITY,
            "business_type": biz_type,
            "biz": biz_info
        },
        OUTPUT_DIR / "servicios" / biz_type / "index.html"
    )
    # About page
    save_rendered(
        "about.html",
        {
            "identity": main.HYDRA_IDENTITY,
            "business_type": biz_type
        },
        OUTPUT_DIR / "quienes-somos" / biz_type / "index.html"
    )
    # Contact page
    save_rendered(
        "contact.html",
        {
            "identity": main.HYDRA_IDENTITY,
            "business_type": biz_type,
            "corporate_emails": main.EMAIL_CONFIG["corporate_emails"]
        },
        OUTPUT_DIR / "contacto" / biz_type / "index.html"
    )

# 3. Legal pages (generated from string formatting)
def save_legal_page(key: str, slug: str):
    """Save a legal page using the string formatting from main.LEGAL_PAGES."""
    from datetime import datetime
    date = datetime.utcnow().strftime("%B %d, %Y")
    html = main.LEGAL_PAGES[key].format(date=date)
    output_path = OUTPUT_DIR / slug / "index.html"
    print(f"Generating legal page {slug} -> {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")

save_legal_page("privacy_policy", "politica-de-privacidad")
save_legal_page("terms_conditions", "terminos-y-condiciones")
save_legal_page("cookies_policy", "politica-de-cookies")

# 4. Copy static assets
static_src = Path("www/static")
static_dest = OUTPUT_DIR / "static"
if static_src.exists():
    shutil.copytree(static_src, static_dest)
else:
    print(f"WARNING: Static source not found: {static_src}")

# Also copy favicon.ico from static to root (templates use /favicon.ico)
favicon_src = static_src / "favicon.ico"
if favicon_src.exists():
    shutil.copy2(favicon_src, OUTPUT_DIR / "favicon.ico")
# Copy banners if any
banner_src = static_src / "banners"
if banner_src.exists():
    shutil.copytree(banner_src, OUTPUT_DIR / "banners")
# Copy images if any
img_src = static_src / "img"
if img_src.exists():
    shutil.copytree(img_src, OUTPUT_DIR / "img")

print(f"\nStatic site generated in {OUTPUT_DIR.resolve()}")
print("To test locally, you can serve with: python -m http.server 8000 --directory _site")