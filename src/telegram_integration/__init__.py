"""Telegram Integration for HYDRA.

Official communication channel: Operator ↔ Hermes ↔ HYDRAS (via CEO).
Credentials loaded from: Security & Secrets Manager → HYDRA config → HYDRA/.env → env vars.
Operator (ID 545786765) auto-authorized if not in allowed users list.

Functions implemented:
- Structured messages (🔴 Action required, 🟡 Important event, 🟢 Summary, ⚪ Status)
- Commands: /estado, /resumen, /alertas, /hydras, /financial, /design, /trading, /tesoreria, /bloqueos, /especialistas, /ayuda
- Action buttons and attachments
- Automatic audit and STATUS.md logging
"""

from .bot import HydraTelegramBot, create_bot_from_env, run_bot

__all__ = ["HydraTelegramBot", "create_bot_from_env", "run_bot"]