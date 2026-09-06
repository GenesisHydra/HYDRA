# -------------------------------------------------------------------------
# YouTube Web Integration – Hydra vertical
# Conecta el conector YouTube con la plataforma web Genesis.
# Renderiza datos públicos de videos/canales en la portada.
# -------------------------------------------------------------------------
import os
from typing import Any, Dict, List, Optional

# Ruta al vault y configuración
VAULT_DIR = "/home/genesis/opt/genesis/HYDRA/config/vault"
ENV_PATH = "/home/genesis/opt/genesis/HYDRA/.env"


def load_env(path: str = ENV_PATH) -> Dict[str, str]:
    """Carga variables del archivo .env."""
    env = {}
    if not os.path.exists(path):
        return env
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip()
    return env


def get_youtube_config() -> Dict[str, str]:
    """Obtiene la configuración de YouTube desde .env o Vault."""
    env = load_env()
    api_key = env.get("YOUTUBE_API_KEY", "")
    channel_id = env.get("YOUTUBE_CHANNEL_ID", "UCBR8-60-B28hp2BmDPdntcQ")
    return {"api_key": api_key, "channel_id": channel_id}


def fetch_youtube_homepage_data() -> Dict[str, Any]:
    """Obtiene datos públicos de YouTube para renderizar en la web.

    Returns:
        dict con videos, channel_info y status.
    """
    from hydra.youtube.connector import YouTubeConnector

    config = get_youtube_config()
    if not config["api_key"]:
        return {"status": "error", "message": "API Key missing", "videos": [], "channel": None}

    try:
        conn = YouTubeConnector()
        # Obtener videos del canal
        videos = conn.search_videos(query="hydra", max_results=3)
        # Obtener detalles del canal
        channel = conn.get_channel_details(config["channel_id"])
        return {
            "status": "ok",
            "videos": videos,
            "channel": channel,
            "channel_id": config["channel_id"],
        }
    except Exception as exc:
        return {"status": "error", "message": str(exc), "videos": [], "channel": None}


def render_youtube_section(data: Optional[Dict[str, Any]] = None) -> str:
    """Genera el HTML del bloque visual de YouTube para la portada.

    Args:
        data: Datos de YouTube. Si es None, se obtienen del API.

    Returns:
        String HTML del bloque YouTube.
    """
    if data is None:
        data = fetch_youtube_homepage_data()

    status = data.get("status", "error")
    videos = data.get("videos", [])
    channel = data.get("channel")

    if status != "ok" or not videos:
        # Fallback con datos estáticos de prueba (mock)
        videos = [
            {"title": "HYDRA - Primer Video de Prueba", "video_id": "pdjzCWo-pTY", "channel_title": "HYDRA Testing"},
            {"title": "Genesis Hydra Platform Demo", "video_id": "ZHNGQscvU4A", "channel_title": "Games FG"},
            {"title": "Hydra Launcher 2026 Guide", "video_id": "ZHNGQscvU4A", "channel_title": "Games FG"},
        ]
        channel = None

    html_parts = []
    html_parts.append('<div id="hydra-youtube" class="youtube-vertical">')
    html_parts.append('  <div class="youtube-header">')
    html_parts.append('    <h2 class="youtube-title">HYDRA YouTube</h2>')
    html_parts.append('    <span class="youtube-badge">1ª Vertical</span>')
    html_parts.append('  </div>')

    if channel:
        channel_title = channel.get("snippet", {}).get("title", "YouTube Channel")
        subscriber_count = channel.get("statistics", {}).get("subscriberCount", "0")
        html_parts.append(f'  <div class="youtube-channel-info">')
        html_parts.append(f'    <span class="channel-name">{channel_title}</span>')
        html_parts.append(f'    <span class="channel-subscribers">{subscriber_count} suscriptores</span>')
        html_parts.append('  </div>')

    html_parts.append('  <div class="youtube-videos">')
    for video in videos:
        video_id = video.get("video_id", "")
        title = video.get("title", "Sin título")
        channel_title = video.get("channel_title", "")
        if video_id:
            embed_url = f"https://www.youtube.com/embed/{video_id}"
            html_parts.append(f'    <div class="youtube-video-card">')
            html_parts.append(f'      <div class="youtube-thumbnail">')
            html_parts.append(f'        <img src="https://img.youtube.com/vi/{video_id}/hqdefault.jpg" alt="{title}" loading="lazy">')
            html_parts.append(f'        <span class="play-icon">&#9654;</span>')
            html_parts.append(f'      </div>')
            html_parts.append(f'      <div class="youtube-video-info">')
            html_parts.append(f'        <h3 class="video-title">{title[:60]}...</h3>')
            html_parts.append(f'        <p class="video-channel">{channel_title}</p>')
            html_parts.append(f'      </div>')
            html_parts.append(f'    </div>')
        else:
            html_parts.append(f'    <div class="youtube-video-card">')
            html_parts.append(f'      <div class="youtube-thumbnail placeholder">')
            html_parts.append(f'        <span>Video</span>')
            html_parts.append(f'      </div>')
            html_parts.append(f'      <div class="youtube-video-info">')
            html_parts.append(f'        <h3 class="video-title">{title[:60]}</h3>')
            html_parts.append(f'        <p class="video-channel">{channel_title}</p>')
            html_parts.append(f'      </div>')
            html_parts.append(f'    </div>')

    html_parts.append('  </div>')
    html_parts.append('</div>')
    return "\n".join(html_parts)


# -------------------------------------------------------------------------
# CSS para la sección YouTube
# -------------------------------------------------------------------------
YOUTUBE_CSS = """
#hydra-youtube {
    background: #0f0f0f;
    color: #ffffff;
    padding: 48px 24px;
    font-family: 'Montserrat', sans-serif;
}
.youtube-header {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 32px;
}
.youtube-title {
    font-size: 2rem;
    font-weight: 700;
    color: #ffffff;
    margin: 0;
}
.youtube-badge {
    background: #e94a4a;
    color: #fff;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
}
.youtube-channel-info {
    display: flex;
    gap: 24px;
    margin-bottom: 24px;
    font-size: 0.9rem;
    color: #aaa;
}
.channel-name {
    font-weight: 600;
    color: #fff;
}
.youtube-videos {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 20px;
}
.youtube-video-card {
    background: #1a1a2e;
    border-radius: 12px;
    overflow: hidden;
    transition: transform 0.2s, box-shadow 0.2s;
    cursor: pointer;
}
.youtube-video-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(233, 74, 74, 0.3);
}
.youtube-thumbnail {
    position: relative;
    width: 100%;
    padding-top: 56.25%;
    background: #000;
}
.youtube-thumbnail img {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
}
.youtube-thumbnail.placeholder {
    display: flex;
    align-items: center;
    justify-content: center;
    color: #666;
    font-size: 1.5rem;
}
.play-icon {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-size: 2.5rem;
    color: #fff;
    text-shadow: 0 2px 8px rgba(0,0,0,0.5);
}
.youtube-video-info {
    padding: 12px 16px;
}
.video-title {
    font-size: 0.95rem;
    font-weight: 600;
    margin: 0 0 4px;
    color: #fff;
    line-height: 1.3;
}
.video-channel {
    font-size: 0.8rem;
    color: #999;
    margin: 0;
}
"""
