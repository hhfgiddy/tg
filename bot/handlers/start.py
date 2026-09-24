from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.database.users import create_or_update_user
from bot.keyboards.main import main_menu
from bot.handlers.contest_participation import (
    process_start_participation,
)


router = Router()


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    user = message.from_user

    create_or_update_user(
        telegram_user_id=user.id,
        username=user.username,
        first_name=user.first_name,
    )

    args = message.text.split(maxsplit=1)

    if len(args) > 1:
        start_parameter = args[1]

        if start_parameter.startswith("contest_"):
            try:
                contest_id = int(
                    start_parameter.split("_", 1)[1]
                )
            except (ValueError, IndexError):
                await message.answer(
                    "❌ Konkurs havolasi noto‘g‘ri."
                )
                return

            await process_start_participation(
                message=message,
                contest_id=contest_id,
            )
            return

    first_name = (
        user.first_name
        or "foydalanuvchi"
    )

    await message.answer(
        f"Assalomu alaykum, {first_name}!\n\n"
        "🎉 Konkurs_uzbot ga xush kelibsiz!\n\n"
        "Bu bot orqali Telegram konkurslarini "
        "yaratish va boshqarish mumkin.",
        reply_markup=main_menu(user_id=user.id),
    )