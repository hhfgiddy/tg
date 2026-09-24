from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def required_channels_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Yana kanal qo‘shish",
                    callback_data="required_add",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⏭ O‘tkazib yuborish",
                    callback_data="required_skip",
                ),
                InlineKeyboardButton(
                    text="✅ Tayyor",
                    callback_data="required_done",
                ),
            ],
        ]
    )


def editing_required_channels_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Yana kanal qo‘shish",
                    callback_data="required_add",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⏭ O‘tkazib yuborish",
                    callback_data="required_skip",
                ),
                InlineKeyboardButton(
                    text="✅ Tayyor",
                    callback_data="required_done",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ Tahrirlashni bekor qilish",
                    callback_data="edit_cancel",
                )
            ],
        ]
    )


def end_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⏰ Vaqt bo‘yicha",
                    callback_data="end_time",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👥 Ishtirokchilar soni bo‘yicha",
                    callback_data="end_participants",
                )
            ],
        ]
    )


def editing_end_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⏰ Vaqt bo‘yicha",
                    callback_data="end_time",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👥 Ishtirokchilar soni bo‘yicha",
                    callback_data="end_participants",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Tahrirlashni bekor qilish",
                    callback_data="edit_cancel",
                )
            ],
        ]
    )


def start_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 Hozir boshlash",
                    callback_data="start_now",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📅 Keyinroq boshlash",
                    callback_data="start_later",
                )
            ],
        ]
    )


def confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Tahrirlash",
                    callback_data="contest_edit",
                ),
                InlineKeyboardButton(
                    text="❌ Bekor qilish",
                    callback_data="contest_cancel",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✅ Tasdiqlash",
                    callback_data="contest_confirm",
                )
            ],
        ]
    )


def edit_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📢 Kanal",
                    callback_data="edit_channel",
                ),
                InlineKeyboardButton(
                    text="📝 Post",
                    callback_data="edit_post",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📋 Obuna kanallari",
                    callback_data="edit_required",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔴 Tugash sharti",
                    callback_data="edit_end",
                ),
                InlineKeyboardButton(
                    text="🏆 G‘oliblar",
                    callback_data="edit_winners",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🎟 Tugma",
                    callback_data="edit_button",
                ),
                InlineKeyboardButton(
                    text="🟢 Boshlanish",
                    callback_data="edit_start",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Previewga qaytish",
                    callback_data="edit_back",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Tahrirlashni bekor qilish",
                    callback_data="edit_cancel",
                )
            ],
        ]
    )


def edit_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Tahrirlashni bekor qilish",
                    callback_data="edit_cancel",
                )
            ]
        ]
    )


def participation_keyboard(
    contest_id: int,
    bot_username: str,
    button_text: str = "🎟 Ishtirok etish",
    participant_count: int = 0,
) -> InlineKeyboardMarkup:

    if participant_count > 0:
        final_text = f"{button_text} ({participant_count})"
    else:
        final_text = button_text

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=final_text,
                    url=(
                        f"https://t.me/{bot_username}"
                        f"?start=contest_{contest_id}"
                    ),
                )
            ]
        ]
    )


def subscription_check_keyboard(
    contest_id: int,
    channels: list[dict],
) -> InlineKeyboardMarkup:

    buttons = []

    for channel in channels:
        username = channel.get("channel_username")
        invite_link = channel.get("invite_link")
        title = channel.get("channel_title") or "Kanal"

        if invite_link:
            url = invite_link
        elif username:
            url = f"https://t.me/{username.lstrip('@')}"
        else:
            continue

        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"➕ {title}",
                    url=url,
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔄 Tekshirish",
                callback_data=f"contest_check:{contest_id}",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )