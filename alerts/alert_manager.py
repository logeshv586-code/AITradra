"""
ALERT MANAGER — Multi-Channel Broadcast (100% OSS)
Sends trading signals via Telegram Bot, Discord Webhook, and Email (SMTP).
All channels are optional — graceful skip if not configured.
"""

import asyncio
import smtplib
from email.mime.text import MIMEText
from dataclasses import dataclass
from typing import Optional
from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TradingAlert:
    ticker: str
    action: str              # BUY / SELL / WATCH / ARBITRAGE / EARNINGS
    confidence: float
    price: float
    reasoning: str
    source_agent: str
    urgency: str             # HIGH / MEDIUM / LOW
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None


class AlertManager:
    """Broadcasts trading alerts to Telegram, Discord, and Email."""

    def __init__(self, config: dict = None):
        config = config or {}
        self.telegram_token = config.get("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = config.get("TELEGRAM_CHAT_ID")
        self.discord_webhook = config.get("DISCORD_WEBHOOK_URL")
        self.smtp_config = {
            "host": config.get("SMTP_HOST", "smtp.gmail.com"),
            "port": int(config.get("SMTP_PORT", 587)),
            "user": config.get("SMTP_USER"),
            "pass": config.get("SMTP_PASS"),
            "to": config.get("ALERT_EMAIL"),
        }

    async def send(self, alert: TradingAlert) -> None:
        """Broadcast alert to all configured channels."""
        message = self._format_message(alert)
        tasks = []

        if self.telegram_token and self.telegram_chat_id:
            tasks.append(self._send_telegram(message))
        if self.discord_webhook:
            tasks.append(self._send_discord(message, alert))
        if self.smtp_config.get("user"):
            tasks.append(self._send_email(alert, message))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            logger.info(f"[AlertManager] No channels configured. Alert logged: {alert.action} {alert.ticker}")

    def _format_message(self, alert: TradingAlert) -> str:
        urgency_emoji = {"HIGH": "🚨", "MEDIUM": "⚠️", "LOW": "ℹ️"}.get(alert.urgency, "📊")
        action_emoji = {"BUY": "🟢", "SELL": "🔴", "WATCH": "👀", "ARBITRAGE": "⚡"}.get(alert.action, "📊")

        lines = [
            f"{urgency_emoji} AXIOM ALERT",
            f"{action_emoji} {alert.action}: {alert.ticker}",
            f"💰 Price: ${alert.price:.4f}",
            f"📊 Confidence: {alert.confidence:.0%}",
            f"🤖 Agent: {alert.source_agent}",
            f"💡 {alert.reasoning[:200]}",
        ]
        if alert.target_price:
            lines.insert(3, f"🎯 Target: ${alert.target_price:.4f}")
        if alert.stop_loss:
            lines.insert(4, f"🛑 Stop: ${alert.stop_loss:.4f}")

        return "\n".join(lines)

    async def _send_telegram(self, message: str) -> None:
        try:
            import httpx
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            async with httpx.AsyncClient() as client:
                await client.post(url, json={"chat_id": self.telegram_chat_id, "text": message})
        except Exception as e:
            logger.error(f"Telegram alert failed: {e}")

    async def _send_discord(self, message: str, alert: TradingAlert) -> None:
        try:
            import httpx
            color = 0x00ff00 if alert.action == "BUY" else (0xff0000 if alert.action == "SELL" else 0xffff00)
            payload = {"embeds": [{"title": f"AXIOM: {alert.action} {alert.ticker}", "description": message, "color": color}]}
            async with httpx.AsyncClient() as client:
                await client.post(self.discord_webhook, json=payload)
        except Exception as e:
            logger.error(f"Discord alert failed: {e}")

    async def _send_email(self, alert: TradingAlert, message: str) -> None:
        try:
            msg = MIMEText(message)
            msg["Subject"] = f"AXIOM Alert: {alert.action} {alert.ticker} ({alert.urgency})"
            msg["From"] = self.smtp_config["user"]
            msg["To"] = self.smtp_config["to"]
            with smtplib.SMTP(self.smtp_config["host"], self.smtp_config["port"]) as server:
                server.starttls()
                server.login(self.smtp_config["user"], self.smtp_config["pass"])
                server.send_message(msg)
        except Exception as e:
            logger.error(f"Email alert failed: {e}")
