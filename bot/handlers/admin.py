from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from bot.config import ADMIN_ID
from bot.database.db import get_connection
from bot.keyboards.admin import (
    admin_panel_keyboard,
    admin_users_keyboard,
    admin_contests_keyboard,
)
from bot.states.admin import AdminStates


router = Router()


USERS_PER_PAGE = 10
CONTESTS_PER_PAGE = 10


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def get_admin_statistics() -> dict:
    with get_connection() as connection:
        users_count = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM users
            """
        ).fetchone()["count"]

        contests_count = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM contests
            """
        ).fetchone()["count"]

        active_count = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM contests
            WHERE status = 'active'
            """
        ).fetchone()["count"]

        finished_count = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM contests
            WHERE status = 'finished'
            """
        ).fetchone()["count"]

    return {
        "users": users_count,
        "contests": contests_count,
        "active": active_count,
        "finished": finished_count,
    }


def admin_panel_text() -> str:
    statistics = get_admin_statistics()

    return (
        "👑 <b>Admin panel</b>\n\n"
        f"👥 Foydalanuvchilar: "
        f"<b>{statistics['users']}</b>\n"
        f"🎉 Konkurslar: "
        f"<b>{statistics['contests']}</b>\n"
        f"🟢 Faol konkurslar: "
        f"<b>{statistics['active']}</b>\n"
        f"🏁 Tugagan konkurslar: "
        f"<b>{statistics['finished']}</b>"
    )


def get_users_page(page: int) -> tuple[list, int]:
    with get_connection() as connection:
        total_users = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM users
            """
        ).fetchone()["count"]

        total_pages = max(
            1,
            (
                total_users
                + USERS_PER_PAGE
                - 1
            )
            // USERS_PER_PAGE,
        )

        page = max(
            0,
            min(
                page,
                total_pages - 1,
            ),
        )

        offset = page * USERS_PER_PAGE

        users = connection.execute(
            """
            SELECT
                telegram_user_id,
                username,
                first_name,
                created_at
            FROM users
            ORDER BY id DESC
            LIMIT ?
            OFFSET ?
            """,
            (
                USERS_PER_PAGE,
                offset,
            ),
        ).fetchall()

    return users, total_pages


def format_users_page(
    users: list,
    page: int,
    total_pages: int,
) -> str:
    text = "👥 <b>Foydalanuvchilar</b>\n\n"

    if not users:
        return text + "Hozircha foydalanuvchilar yo‘q."

    start_number = (
        page * USERS_PER_PAGE
    ) + 1

    for index, user in enumerate(users):
        number = start_number + index

        first_name = (
            user["first_name"]
            or "Noma'lum"
        )

        username = user["username"]

        if username:
            profile_name = (
                f"{first_name} "
                f"(@{username})"
            )
        else:
            profile_name = first_name

        profile_link = (
            f'<a href="tg://user?id='
            f'{user["telegram_user_id"]}">'
            f'{profile_name}</a>'
        )

        text += (
            f"<b>{number}.</b> "
            f"{profile_link}\n"
            f"   🆔 <code>"
            f'{user["telegram_user_id"]}'
            f"</code>\n\n"
        )

    text += (
        f"📄 Sahifa: "
        f"<b>{page + 1}/{total_pages}</b>"
    )

    return text


def get_contests_page(page: int) -> tuple[list, int]:
    with get_connection() as connection:
        total_contests = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM contests
            """
        ).fetchone()["count"]

        total_pages = max(
            1,
            (
                total_contests
                + CONTESTS_PER_PAGE
                - 1
            )
            // CONTESTS_PER_PAGE,
        )

        page = max(
            0,
            min(
                page,
                total_pages - 1,
            ),
        )

        offset = page * CONTESTS_PER_PAGE

        contests = connection.execute(
            """
            SELECT
                c.id,
                c.owner_id,
                c.channel_title,
                c.channel_username,
                c.status,
                c.winners_count,
                u.telegram_user_id,
                u.username,
                u.first_name
            FROM contests c
            LEFT JOIN users u
                ON u.id = c.owner_id
            ORDER BY c.id DESC
            LIMIT ?
            OFFSET ?
            """,
            (
                CONTESTS_PER_PAGE,
                offset,
            ),
        ).fetchall()

    return contests, total_pages


def get_status_text(status: str) -> str:
    if status == "scheduled":
        return "⏳ Rejalashtirilgan"

    if status == "active":
        return "🟢 Faol"

    if status == "finished":
        return "🏁 Tugagan"

    if status == "cancelled":
        return "❌ Bekor qilingan"

    return status


def format_contests_page(
    contests: list,
    page: int,
    total_pages: int,
) -> str:
    text = "🎉 <b>Konkurslar</b>\n\n"

    if not contests:
        return text + "Hozircha konkurslar yo‘q."

    start_number = (
        page * CONTESTS_PER_PAGE
    ) + 1

    for index, contest in enumerate(contests):
        number = start_number + index

        channel_title = (
            contest["channel_title"]
            or contest["channel_username"]
            or "Noma'lum kanal"
        )

        status = get_status_text(
            contest["status"]
        )

        owner_name = (
            contest["first_name"]
            or "Noma'lum"
        )

        owner_username = contest["username"]

        if owner_username:
            owner_text = (
                f"{owner_name} "
                f"(@{owner_username})"
            )
        else:
            owner_text = owner_name

        owner_link = (
            f'<a href="tg://user?id='
            f'{contest["telegram_user_id"]}">'
            f'{owner_text}</a>'
        )

        text += (
            f"<b>{number}. Konkurs "
            f"#{contest['id']}</b>\n"
            f"📢 Kanal: "
            f"{channel_title}\n"
            f"👤 Egasi: "
            f"{owner_link}\n"
            f"📊 Holati: "
            f"{status}\n"
            f"🏆 G‘oliblar: "
            f"{contest['winners_count']}\n\n"
        )

    text += (
        f"📄 Sahifa: "
        f"<b>{page + 1}/{total_pages}</b>"
    )

    return text


@router.message(F.text == "👑 Admin panel")
async def admin_panel_handler(
    message: Message,
) -> None:
    if not is_admin(message.from_user.id):
        return

    await message.answer(
        admin_panel_text(),
        reply_markup=admin_panel_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(
    F.data.startswith("admin_users:")
)
async def admin_users_handler(
    callback: CallbackQuery,
) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "❌ Siz admin emassiz.",
            show_alert=True,
        )
        return

    try:
        page = int(
            callback.data.split(":", 1)[1]
        )
    except (ValueError, IndexError):
        page = 0

    users, total_pages = get_users_page(page)

    page = max(
        0,
        min(
            page,
            total_pages - 1,
        ),
    )

    text = format_users_page(
        users=users,
        page=page,
        total_pages=total_pages,
    )

    await callback.message.edit_text(
        text,
        reply_markup=admin_users_keyboard(
            page=page,
            total_pages=total_pages,
        ),
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(
    F.data.startswith("admin_contests:")
)
async def admin_contests_handler(
    callback: CallbackQuery,
) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "❌ Siz admin emassiz.",
            show_alert=True,
        )
        return

    try:
        page = int(
            callback.data.split(":", 1)[1]
        )
    except (ValueError, IndexError):
        page = 0

    contests, total_pages = get_contests_page(page)

    page = max(
        0,
        min(
            page,
            total_pages - 1,
        ),
    )

    text = format_contests_page(
        contests=contests,
        page=page,
        total_pages=total_pages,
    )

    await callback.message.edit_text(
        text,
        reply_markup=admin_contests_keyboard(
            page=page,
            total_pages=total_pages,
        ),
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(F.data == "admin_back")
async def admin_back_handler(
    callback: CallbackQuery,
) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "❌ Siz admin emassiz.",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        admin_panel_text(),
        reply_markup=admin_panel_keyboard(),
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(F.data == "admin_statistics")
async def admin_statistics_handler(
    callback: CallbackQuery,
) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "❌ Siz admin emassiz.",
            show_alert=True,
        )
        return

    statistics = get_admin_statistics()

    await callback.answer(
        (
            f"👥 Users: {statistics['users']}\n"
            f"🎉 Konkurslar: {statistics['contests']}\n"
            f"🟢 Faol: {statistics['active']}\n"
            f"🏁 Tugagan: {statistics['finished']}"
        ),
        show_alert=True,
    )


@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "❌ Siz admin emassiz.",
            show_alert=True,
        )
        return

    await state.set_state(
        AdminStates.waiting_for_broadcast
    )

    await callback.message.answer(
        "📢 <b>Xabar yuborish</b>\n\n"
        "Barcha foydalanuvchilarga yubormoqchi "
        "bo‘lgan xabaringizni yuboring.\n\n"
        "Matn, rasm, video yoki boshqa Telegram "
        "xabarini yuborishingiz mumkin.\n\n"
        "❌ Bekor qilish uchun /cancel yozing.",
        parse_mode="HTML",
    )

    await callback.answer()


@router.message(
    AdminStates.waiting_for_broadcast
)
async def process_broadcast(
    message: Message,
    state: FSMContext,
) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    if message.text == "/cancel":
        await state.clear()

        await message.answer(
            "❌ Xabar yuborish bekor qilindi.",
            reply_markup=admin_panel_keyboard(),
        )
        return

    with get_connection() as connection:
        users = connection.execute(
            """
            SELECT telegram_user_id
            FROM users
            """
        ).fetchall()

    total = len(users)
    success = 0
    failed = 0

    status_message = await message.answer(
        "📤 Xabar yuborilmoqda...\n\n"
        f"👥 Jami: {total}"
    )

    for user in users:
        try:
            await message.bot.copy_message(
                chat_id=user["telegram_user_id"],
                from_chat_id=message.chat.id,
                message_id=message.message_id,
            )

            success += 1

        except Exception:
            failed += 1

    await state.clear()

    try:
        await status_message.edit_text(
            "📢 <b>Broadcast tugadi</b>\n\n"
            f"👥 Jami: <b>{total}</b>\n"
            f"✅ Yuborildi: <b>{success}</b>\n"
            f"❌ Yuborilmadi: <b>{failed}</b>",
            reply_markup=admin_panel_keyboard(),
            parse_mode="HTML",
        )
    except TelegramBadRequest:
        await message.answer(
            "📢 <b>Broadcast tugadi</b>\n\n"
            f"👥 Jami: <b>{total}</b>\n"
            f"✅ Yuborildi: <b>{success}</b>\n"
            f"❌ Yuborilmadi: <b>{failed}</b>",
            reply_markup=admin_panel_keyboard(),
            parse_mode="HTML",
        )