import asyncio
import logging

from aiogram import Bot, Dispatcher

from bot.config import BOT_TOKEN
from bot.database.db import init_database

from bot.handlers.start import router as start_router
from bot.handlers.contest_create import (
    router as contest_create_router,
)
from bot.handlers.contest_participation import (
    router as contest_participation_router,
)
from bot.handlers.my_contests import (
    router as my_contests_router,
)
from bot.handlers.admin import (
    router as admin_router,
)
from bot.handlers.help import (
    router as help_router,
)

from bot.scheduler import start_scheduler
from bot.webapp.server import start_web_server


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    print("MAIN ISHLAYAPTI")

    init_database()

    bot = Bot(
        token=BOT_TOKEN
    )

    dp = Dispatcher()

    dp.include_router(start_router)
    dp.include_router(my_contests_router)
    dp.include_router(contest_create_router)
    dp.include_router(contest_participation_router)
    dp.include_router(admin_router)
    dp.include_router(help_router)

    print("SCHEDULER ISHLAYAPTI")

    start_scheduler(bot)

    print("WEBAPP SERVER ISHLAYAPTI")

    web_runner, web_site = await start_web_server(
        bot=bot,
        host="0.0.0.0",
        port=8080,
    )

    print("POLLING BOSHLAYAPTI")

    try:
        await dp.start_polling(bot)

    finally:
        await web_runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())