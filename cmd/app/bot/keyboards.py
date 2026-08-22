from aiogram.types import InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.formatting import STATUS_EMOJI, STATUS_RU

BTN_LEADS = "📋 Заявки"
BTN_STATS = "📊 Статистика"
BTN_TOP = "🏆 Топ товаров"
BTN_FIND = "🔍 Поиск по каталогу"
BTN_CANCEL = "✖️ Отмена"

STATUS_ORDER = ("new", "in_progress", "done")

FILTERS = (
    ("all", "Все"),
    ("new", "🆕"),
    ("prog", "🔧"),
    ("done", "✅"),
)

CODE_TO_STATUS = {"all": None, "new": "new", "prog": "in_progress", "done": "done"}


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_LEADS)],
            [KeyboardButton(text=BTN_STATS), KeyboardButton(text=BTN_TOP)],
            [KeyboardButton(text=BTN_FIND)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие…",
    )


def search_prompt_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_CANCEL)]],
        resize_keyboard=True,
        input_field_placeholder="Название или бренд…",
    )


def _status_btn_label(status_value: str, current: str) -> str:
    label = f"{STATUS_EMOJI[status_value]} {STATUS_RU[status_value]}"
    return f"• {label} •" if status_value == current else label


def lead_card_kb(lead_id: int, current: str = "new", ctx: str = "-"):
    builder = InlineKeyboardBuilder()
    for status_value in STATUS_ORDER:
        builder.button(
            text=_status_btn_label(status_value, current),
            callback_data=f"lst:{lead_id}:{status_value}:{ctx}",
        )
    builder.adjust(3)
    markup = builder.as_markup()
    if ctx != "-":
        fid, page = ctx.split(":")
        markup.inline_keyboard.append(
            [InlineKeyboardButton(text="⬅️ К списку", callback_data=f"lb:{fid}:{int(page)}")]
        )
    return markup


lead_status_kb = lead_card_kb


def lead_list_kb(leads, fid: str, page: int, pages: int):
    builder = InlineKeyboardBuilder()
    for lead in leads:
        name = (lead.name or "")[:20]
        builder.button(
            text=f"{STATUS_EMOJI.get(lead.status, '❔')} #{lead.id} · {name}",
            callback_data=f"lv:{fid}:{page}:{lead.id}",
        )
    if leads:
        builder.adjust(1)
    markup = builder.as_markup()

    filter_row = [
        InlineKeyboardButton(
            text=("• " if code == fid else "") + label,
            callback_data=f"lf:{code}",
        )
        for code, label in FILTERS
    ]
    markup.inline_keyboard.append(filter_row)

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="◀️", callback_data=f"lb:{fid}:{page - 1}"))
    nav_row.append(
        InlineKeyboardButton(text=f"{page + 1}/{max(pages, 1)}", callback_data="noop")
    )
    if page < pages - 1:
        nav_row.append(InlineKeyboardButton(text="▶️", callback_data=f"lb:{fid}:{page + 1}"))
    markup.inline_keyboard.append(nav_row)
    return markup
