from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def help_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Konkurs yaratish",
                    callback_data="help_create_contest",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📋 Konkurslarim",
                    callback_data="help_my_contests",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🎟 Konkursda qatnashish",
                    callback_data="help_participation",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🏆 G‘oliblar",
                    callback_data="help_winners",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❓ FAQ",
                    callback_data="help_faq",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="👨‍💻 Admin bilan bog‘lanish",
                    callback_data="help_admin",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Orqaga",
                    callback_data="help_back",
                ),
            ],
        ]
    )