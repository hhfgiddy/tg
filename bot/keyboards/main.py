from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from bot.config import ADMIN_ID


def main_menu(user_id: int | None = None) -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton(text="➕ Konkurs yaratish"),
            KeyboardButton(text="📋 Konkurslarim"),
        ],
    ]

    if user_id == ADMIN_ID:
        keyboard.append(
            [
                KeyboardButton(text="👑 Admin panel"),
            ]
        )

    keyboard.append(
        [
            KeyboardButton(text="ℹ️ Yordam"),
        ]
    )

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
    )