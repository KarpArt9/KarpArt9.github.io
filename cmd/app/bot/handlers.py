import logging
import math
from datetime import timedelta

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select

from app.bot.formatting import (
    CATEGORY_RU,
    STATUS_RU,
    esc,
    fmt_price,
    plural,
)
from app.bot.keyboards import (
    BTN_CANCEL,
    BTN_FIND,
    BTN_LEADS,
    BTN_STATS,
    BTN_TOP,
    CODE_TO_STATUS,
    main_menu_kb,
    lead_card_kb,
    lead_list_kb,
    search_prompt_kb,
)
from app.database import SessionLocal
from app.models import Lead, Product

logger = logging.getLogger(__name__)

router = Router(name="bot")

PAGE_SIZE = 8
SEARCH_LIMIT = 8
AWAITING_SEARCH: set[int] = set()

FILTER_TITLES = {
    "all": "Все",
    "new": "🆕 Новые",
    "prog": "🔧 В работе",
    "done": "✅ Выполненные",
}

WELCOME_TEXT = (
    "❄️ <b>Бот «Райский холод»</b>\n\n"
    "Здесь появляются все заявки с сайта и работают кнопки:\n\n"
    f"{BTN_LEADS} — список заявок с фильтрами\n"
    f"{BTN_STATS} — статистика по дням и статусам\n"
    f"{BTN_TOP} — самые заказываемые товары\n"
    f"{BTN_FIND} — поиск по каталогу\n\n"
    "Новые заявки приходят автоматически — статус можно "
    "менять прямо из уведомления."
)


def _area_note(product: Product) -> str:
    return f" · до {product.area} м²" if getattr(product, "area", None) else ""


def _product_line(product: Product) -> str:
    kind = "инвертор" if product.type == "inverter" else "стандарт"
    return f"{CATEGORY_RU.get(product.category, product.category)} · {kind}{_area_note(product)}"


# ---------------------------------------------------------------- заявки


async def load_leads_page(fid: str, page: int):
    async with SessionLocal() as session:
        base = select(Lead)
        status_value = CODE_TO_STATUS.get(fid)
        if status_value:
            base = base.where(Lead.status == status_value)
        total = await session.scalar(select(func.count()).select_from(base.subquery())) or 0
        rows = (
            await session.execute(
                base.order_by(Lead.created_at.desc(), Lead.id.desc())
                .offset(page * PAGE_SIZE)
                .limit(PAGE_SIZE)
            )
        ).scalars().all()
    pages = max(1, math.ceil(total / PAGE_SIZE))
    return total, pages, rows


def leads_list_text(total: int, page: int, pages: int, fid: str) -> str:
    return (
        f"📋 <b>Заявки</b> · {FILTER_TITLES[fid]}\n"
        f"Всего: {total} {plural(total, 'заявка', 'заявки', 'заявок')} · "
        f"страница {page + 1}/{pages}\n\n"
        "Нажмите на заявку ниже, чтобы открыть карточку."
    )


async def show_leads_list(message: Message, fid: str, page: int) -> None:
    total, pages, rows = await load_leads_page(fid, page)
    await message.answer(
        leads_list_text(total, page, pages, fid),
        reply_markup=lead_list_kb(rows, fid, page, pages),
    )


async def edit_leads_list(callback: CallbackQuery, fid: str, page: int) -> None:
    total, pages, rows = await load_leads_page(fid, page)
    try:
        await callback.message.edit_text(
            leads_list_text(total, page, pages, fid),
            reply_markup=lead_list_kb(rows, fid, page, pages),
        )
    except TelegramBadRequest as exc:
        if "not modified" not in str(exc):
            raise
    await callback.answer()


async def render_lead_view(lead_id: int, ctx: str):
    async with SessionLocal() as session:
        lead = await session.get(Lead, lead_id)
        if not lead:
            return None
        product_name = None
        if lead.product_id:
            product_name = await session.scalar(
                select(Product.name).where(Product.id == lead.product_id)
            )

    from app.services.telegram import format_lead_card

    text = format_lead_card(lead, product_name)
    return text, lead_card_kb(lead.id, lead.status, ctx)


# ---------------------------------------------------------------- команды и меню


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    AWAITING_SEARCH.discard(message.from_user.id)
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_kb())


@router.message(Command("help"))
@router.message(F.text == "❓ Помощь")
async def cmd_help(message: Message) -> None:
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_kb())


@router.message(Command("leads"))
@router.message(F.text == BTN_LEADS)
async def cmd_leads(message: Message) -> None:
    AWAITING_SEARCH.discard(message.from_user.id)
    await show_leads_list(message, "all", 0)


@router.message(Command("stats"))
@router.message(F.text == BTN_STATS)
async def cmd_stats(message: Message) -> None:
    AWAITING_SEARCH.discard(message.from_user.id)

    now = utcnow_naive()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=6)

    async with SessionLocal() as session:
        total = await session.scalar(select(func.count()).select_from(Lead)) or 0
        today = (
            await session.scalar(
                select(func.count()).select_from(Lead).where(Lead.created_at >= today_start)
            )
            or 0
        )
        week = (
            await session.scalar(
                select(func.count()).select_from(Lead).where(Lead.created_at >= week_start)
            )
            or 0
        )
        by_status_rows = (
            await session.execute(select(Lead.status, func.count()).group_by(Lead.status))
        ).all()
    by_status = {status: count for status, count in by_status_rows}

    lines = [
        "📊 <b>Статистика заявок</b>",
        "",
        f"🕒 За сегодня: <b>{today}</b>",
        f"📅 За неделю: <b>{week}</b>",
        f"Σ Всего: <b>{total}</b> {plural(total, 'заявка', 'заявки', 'заявок')}",
        "",
        f"🆕 Новых: <b>{by_status.get('new', 0)}</b>",
        f"🔧 В работе: <b>{by_status.get('in_progress', 0)}</b>",
        f"✅ Выполнено: <b>{by_status.get('done', 0)}</b>",
    ]
    await message.answer("\n".join(lines))


@router.message(Command("top"))
@router.message(F.text == BTN_TOP)
async def cmd_top(message: Message) -> None:
    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(Product.name, func.count().label("cnt"))
                .join(Lead, Lead.product_id == Product.id)
                .group_by(Product.id, Product.name)
                .order_by(func.count().desc())
                .limit(10)
            )
        ).all()

    if not rows:
        await message.answer("Пока нет заказов конкретных товаров.")
        return

    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆 <b>Топ товаров по заказам</b>", ""]
    for index, (name, count) in enumerate(rows, start=1):
        prefix = medals[index - 1] if index <= 3 else f"{index}."
        lines.append(
            f"{prefix} {esc(name)} — <b>{count}</b> "
            f"{plural(count, 'заказ', 'заказа', 'заказов')}"
        )
    await message.answer("\n".join(lines))


async def run_search(chat: Message | CallbackQuery, query_text: str) -> Message:
    pattern = f"%{query_text}%"
    async with SessionLocal() as session:
        found = (
            await session.execute(
                select(Product)
                .where(
                    Product.is_active.is_(True),
                    (Product.name.ilike(pattern)) | (Product.brand.ilike(pattern)),
                )
                .order_by(Product.price)
                .limit(SEARCH_LIMIT)
            )
        ).scalars().all()

    if not found:
        text = (
            f"🔍 По запросу «{esc(query_text)}» ничего не найдено.\n"
            "Попробуйте бренд (ballu, hisense) или модель."
        )
    else:
        lines = [
            f"🔍 Нашёл <b>{len(found)}</b> "
            f"{plural(len(found), 'товар', 'товара', 'товаров')} "
            f"по запросу «{esc(query_text)}»:",
            "",
        ]
        for index, product in enumerate(found, start=1):
            lines.append(f"{index}. <b>{esc(product.name)}</b> — {fmt_price(product.price)}")
            lines.append(f"   {_product_line(product)}\n")

    target = chat.message if isinstance(chat, CallbackQuery) else chat
    return await target.answer("\n".join(lines), reply_markup=main_menu_kb())


@router.message(Command("find"))
async def cmd_find(message: Message, command: CommandObject | None = None) -> None:
    query_text = (command.args or "").strip() if command else ""
    if not query_text:
        AWAITING_SEARCH.add(message.from_user.id)
        await message.answer("Введите название или бренд для поиска:", reply_markup=search_prompt_kb())
        return
    await run_search(message, query_text)


@router.message(F.text == BTN_FIND)
async def btn_find(message: Message) -> None:
    AWAITING_SEARCH.add(message.from_user.id)
    await message.answer("Введите название или бренд для поиска:", reply_markup=search_prompt_kb())


@router.message(Command("lead"))
async def cmd_lead(message: Message, command: CommandObject | None = None) -> None:
    args = (command.args or "").strip() if command else ""
    if not args.isdigit():
        await message.answer("Использование: /lead 12")
        return
    view = await render_lead_view(int(args), ctx="-")
    if not view:
        await message.answer(f"Заявка #{args} не найдена")
        return
    await message.answer(view[0], reply_markup=view[1])


# ---------------------------------------------------------------- колбэки


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data.startswith("lf:"))
async def cb_filter(callback: CallbackQuery) -> None:
    fid = callback.data.split(":", 1)[1]
    if fid not in CODE_TO_STATUS:
        await callback.answer("Неизвестный фильтр", show_alert=True)
        return
    await edit_leads_list(callback, fid, 0)


@router.callback_query(F.data.startswith("lb:"))
async def cb_back(callback: CallbackQuery) -> None:
    _, fid, page_raw = callback.data.split(":")
    await edit_leads_list(callback, fid, max(0, int(page_raw)))


@router.callback_query(F.data.startswith("lv:"))
async def cb_lead_view(callback: CallbackQuery) -> None:
    try:
        _, fid, page_raw, lead_id_raw = callback.data.split(":")
        lead_id = int(lead_id_raw)
    except (ValueError, AttributeError):
        await callback.answer("Некорректные данные", show_alert=True)
        return
    view = await render_lead_view(lead_id, ctx=f"{fid}:{page_raw}")
    if not view:
        await callback.answer(f"Заявка #{lead_id} не найдена", show_alert=True)
        return
    try:
        await callback.message.edit_text(view[0], reply_markup=view[1])
    except TelegramBadRequest as exc:
        if "not modified" not in str(exc):
            raise
    await callback.answer()


@router.callback_query(F.data.startswith("lst:"))
async def cb_set_status(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    try:
        lead_id = int(parts[1])
        status_value = parts[2]
        ctx = ":".join(parts[3:]) or "-"
    except (IndexError, ValueError):
        await callback.answer("Некорректные данные", show_alert=True)
        return

    if status_value not in STATUS_RU:
        await callback.answer("Неизвестный статус", show_alert=True)
        return

    async with SessionLocal() as session:
        lead = await session.get(Lead, lead_id)
        if not lead:
            await callback.answer(f"Заявка #{lead_id} не найдена", show_alert=True)
            return
        lead.status = status_value
        await session.commit()
        product_name = None
        if lead.product_id:
            product_name = await session.scalar(
                select(Product.name).where(Product.id == lead.product_id)
            )

    from app.services.telegram import format_lead_card

    try:
        await callback.message.edit_text(
            format_lead_card(lead, product_name),
            reply_markup=lead_card_kb(lead_id, status_value, ctx),
        )
    except TelegramBadRequest as exc:
        if "not modified" not in str(exc):
            raise
    await callback.answer(f"Статус заявки #{lead_id}: {STATUS_RU[status_value]}")


# ---------------------------------------------------------------- свободный текст


@router.message(F.text == BTN_CANCEL)
async def btn_cancel(message: Message) -> None:
    AWAITING_SEARCH.discard(message.from_user.id)
    await message.answer("Отменено 👇", reply_markup=main_menu_kb())


@router.message(F.text)
async def free_text(message: Message) -> None:
    uid = message.from_user.id
    if uid in AWAITING_SEARCH:
        AWAITING_SEARCH.discard(uid)
        await run_search(message, message.text.strip())
        return
    await message.answer(
        "Выберите действие кнопками меню 👇",
        reply_markup=main_menu_kb(),
    )


def utcnow_naive():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(tzinfo=None)


def register(dispatcher) -> None:
    dispatcher.include_router(router)
