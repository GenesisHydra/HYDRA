# -------------------------------------------------------------------------
# HYDRA Web Connector Package
# Permite gestionar la web de HYDRA desde el nucleo de HYDRA.
# Sigue el patron del TelegramConnector: vault + servicio + health_check.
# -------------------------------------------------------------------------
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

__all__ = ["WebService", "WebConnector", "health_check", "WEB_URL_VAULT_KEY"]
