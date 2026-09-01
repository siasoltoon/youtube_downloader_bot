"""Temporary helper for diagnosing Telegram send failures.

Not imported by the bot; kept as a reference for the exact logging pattern to
apply around bot.send_message/bot.send_video calls.
"""

import logging

logger = logging.getLogger(__name__)


async def log_telegram_send(send_callable, *args, **kwargs):
    """Execute a Telegram send operation with explicit start/success/failure logs."""
    logger.info("📨 Telegram send: preparing request")
    try:
        result = await send_callable(*args, **kwargs)
        logger.info("✅ Telegram send: success (message_id=%s)", getattr(result, "message_id", "unknown"))
        return result
    except Exception:
        logger.exception("❌ Telegram send: FAILED")
        raise
