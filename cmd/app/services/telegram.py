import logging

from app.bot.formatting import (
    esc,
    fmt_dt,
    fmt_price,
    kind_label,
    plural,
    status_line,
)
from app.bot.keyboards import lead_card_kb
from app.config import settings
from app.models import Lead

logger = logging.getLogger(__name__)

_bot = None


def set_bot(bot) -> None:
    global _bot
    _bot = bot


def is_enabled() -> bool:
    return _bot is not None and bool(settings.admin_chat_id)


async def send_message(text: str, reply_markup=None) -> bool:
    if not is_enabled():
        logger.warning("Telegram notifications disabled (BOT_TOKEN or ADMIN_CHAT_ID empty)")
        return False
    try:
        await _bot.send_message(
            chat_id=int(settings.admin_chat_id),
            text=text,
            reply_markup=reply_markup,
        )
        return True
    except Exception:
        logger.exception("Telegram send_message failed")
        return False


def format_lead_card(lead: Lead, product_name: str | None = None) -> str:
    lines = [
        f"🧾 <b>Заявка #{lead.id}</b> · {kind_label(lead.kind)}",
    ]
    if lead.name:
        lines.append(f"👤 Имя: {esc(lead.name)}")
    lines.append(f"📱 Телефон: <code>{esc(lead.phone)}</code>")
    if product_name:
        lines.append(f"📦 Товар: <b>{esc(product_name)}</b>")
    if lead.comment:
        lines.append(f"💬 {esc(lead.comment)}")
    created = fmt_dt(lead.created_at)
    lines.append(f"🕒 {created} UTC")
    lines.append(f"📊 Статус: <b>{status_line(lead.status)}</b>")
    return "\n".join(lines)


async def notify_new_lead(lead: Lead, product_name: str | None = None) -> bool:
    return await send_message(
        format_lead_card(lead, product_name),
        reply_markup=lead_card_kb(lead.id, lead.status),
    )
