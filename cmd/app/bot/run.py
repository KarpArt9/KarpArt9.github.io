import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from app.bot import handlers
from app.config import settings
from app.services.telegram import set_bot

logger = logging.getLogger(__name__)

BOT_COMMANDS = [
    BotCommand(command="leads", description="📋 Заявки"),
    BotCommand(command="stats", description="📊 Статистика"),
    BotCommand(command="top", description="🏆 Топ товаров"),
    BotCommand(command="find", description="🔍 Поиск товаров"),
    BotCommand(command="help", description="❓ Помощь"),
]


def create_bot() -> Bot | None:
    if not settings.bot_token:
        logger.warning("BOT_TOKEN is empty, telegram bot disabled")
        return None
    kwargs = {}
    if settings.tg_proxy:
        kwargs["session"] = AiohttpSession(proxy=settings.tg_proxy)
        logger.info("Telegram bot uses proxy %s", settings.tg_proxy)
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        **kwargs,
    )


async def start_bot_safely() -> None:
    bot = create_bot()
    if bot is None:
        return
    try:
        me = await bot.get_me()
    except Exception as exc:
        logger.error("Telegram bot unavailable: %s", exc)
        return

    set_bot(bot)
    dispatcher = Dispatcher()
    handlers.register(dispatcher)

    try:
        await bot.set_my_commands(BOT_COMMANDS)
        logger.info("Bot command menu updated")
    except Exception:
        logger.warning("set_my_commands failed", exc_info=True)

    logger.info("Starting telegram bot polling as @%s", me.username)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dispatcher.start_polling(bot)
    except asyncio.CancelledError:
        logger.info("Bot polling cancelled")
        raise
    except Exception:
        logger.exception("Bot polling crashed")


def launch_task() -> asyncio.Task | None:
    if not settings.bot_token:
        return None
    return asyncio.create_task(start_bot_safely())
