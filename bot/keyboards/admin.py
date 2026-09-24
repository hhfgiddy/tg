from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👥 Foydalanuvchilar",
                    callback_data="admin_users:0",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🎉 Konkurslar",
                    callback_data="admin_contests:0",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📊 Statistika",
                    callback_data="admin_statistics",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📢 Xabar yuborish",
                    callback_data="admin_broadcast",
                ),
            ],
        ]
    )


def admin_users_keyboard(
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    buttons = []

    navigation = []

    if page > 0:
        navigation.append(
            InlineKeyboardButton(
                text="⬅️ Oldingi",
                callback_data=f"admin_users:{page - 1}",
            )
        )

    if page < total_pages - 1:
        navigation.append(
            InlineKeyboardButton(
                text="➡️ Keyingi",
                callback_data=f"admin_users:{page + 1}",
            )
        )

    if navigation:
        buttons.append(navigation)

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 Admin panel",
                callback_data="admin_back",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


def admin_contests_keyboard(
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    buttons = []

    navigation = []

    if page > 0:
        navigation.append(
            InlineKeyboardButton(
                text="⬅️ Oldingi",
                callback_data=f"admin_contests:{page - 1}",
            )
        )

    if page < total_pages - 1:
        navigation.append(
            InlineKeyboardButton(
                text="➡️ Keyingi",
                callback_data=f"admin_contests:{page + 1}",
            )
        )

    if navigation:
        buttons.append(navigation)

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 Admin panel",
                callback_data="admin_back",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )