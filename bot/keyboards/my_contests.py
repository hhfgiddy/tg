from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


CONTESTS_PER_PAGE = 10


def my_contests_keyboard(
    contests,
    page: int = 0,
) -> InlineKeyboardMarkup:
    total_pages = max(
        1,
        (
            len(contests)
            + CONTESTS_PER_PAGE
            - 1
        )
        // CONTESTS_PER_PAGE,
    )

    if page < 0:
        page = 0

    if page >= total_pages:
        page = total_pages - 1

    start = page * CONTESTS_PER_PAGE
    end = start + CONTESTS_PER_PAGE

    page_contests = contests[start:end]

    buttons = []

    for contest in page_contests:
        status = contest["status"]

        if status == "scheduled":
            status_icon = "⏳"

        elif status == "active":
            status_icon = "🟢"

        elif status == "finished":
            status_icon = "🏁"

        elif status == "cancelled":
            status_icon = "❌"

        else:
            status_icon = "❓"

        channel_title = (
            contest["channel_title"]
            or contest["channel_username"]
            or f"Konkurs #{contest['id']}"
        )

        text = (
            f"{status_icon} "
            f"#{contest['id']} "
            f"{channel_title}"
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    text=text[:60],
                    callback_data=(
                        f"my_contest:{contest['id']}"
                    ),
                )
            ]
        )

    navigation_buttons = []

    if page > 0:
        navigation_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Oldingi",
                callback_data=(
                    f"my_contests_page:{page - 1}"
                ),
            )
        )

    if page < total_pages - 1:
        navigation_buttons.append(
            InlineKeyboardButton(
                text="➡️ Keyingi",
                callback_data=(
                    f"my_contests_page:{page + 1}"
                ),
            )
        )

    if navigation_buttons:
        buttons.append(
            navigation_buttons
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔄 Yangilash",
                callback_data="my_contests_refresh",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


def contest_management_keyboard(
    contest_id: int,
    can_cancel: bool,
    can_finish: bool,
) -> InlineKeyboardMarkup:

    buttons = []

    if can_cancel or can_finish:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="✏️ Tahrirlash",
                    callback_data=(
                        f"edit_existing:{contest_id}"
                    ),
                )
            ]
        )

    if can_finish:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🏁 Hozir tugatish",
                    callback_data=(
                        f"finish_contest:{contest_id}"
                    ),
                )
            ]
        )

    if can_cancel:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="❌ Konkursni bekor qilish",
                    callback_data=(
                        f"cancel_contest:{contest_id}"
                    ),
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 Konkurslarim",
                callback_data="my_contests_back",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


def finish_confirmation_keyboard(
    contest_id: int,
) -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏁 Ha tugatish",
                    callback_data=(
                        f"finish_confirm:{contest_id}"
                    ),
                ),
                InlineKeyboardButton(
                    text="🔙 Yo‘q",
                    callback_data=(
                        f"my_contest:{contest_id}"
                    ),
                ),
            ]
        ]
    )


def cancel_confirmation_keyboard(
    contest_id: int,
) -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Ha bekor qilish",
                    callback_data=(
                        f"cancel_confirm:{contest_id}"
                    ),
                ),
                InlineKeyboardButton(
                    text="🔙 Yo‘q",
                    callback_data=(
                        f"my_contest:{contest_id}"
                    ),
                ),
            ]
        ]
    )