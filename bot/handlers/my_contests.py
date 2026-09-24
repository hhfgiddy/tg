from datetime import datetime

from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.db import get_connection
from bot.database.participants import get_participant_count
from bot.keyboards.contest import edit_menu_keyboard
from bot.keyboards.my_contests import (
    cancel_confirmation_keyboard,
    contest_management_keyboard,
    finish_confirmation_keyboard,
    my_contests_keyboard,
)
from bot.scheduler import finish_contest_job
from bot.states.contest import ContestCreateStates


router = Router()


def get_user_database_id(
    telegram_user_id: int,
):
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id
            FROM users
            WHERE telegram_user_id = ?
            """,
            (telegram_user_id,),
        ).fetchone()

        if row is None:
            return None

        return row["id"]


def get_user_contests(
    telegram_user_id: int,
):
    user_id = get_user_database_id(
        telegram_user_id
    )

    if user_id is None:
        return []

    with get_connection() as connection:
        return connection.execute(
            """
            SELECT *
            FROM contests
            WHERE owner_id = ?
            ORDER BY id DESC
            """,
            (user_id,),
        ).fetchall()


def get_owned_contest(
    telegram_user_id: int,
    contest_id: int,
):
    user_id = get_user_database_id(
        telegram_user_id
    )

    if user_id is None:
        return None

    with get_connection() as connection:
        return connection.execute(
            """
            SELECT *
            FROM contests
            WHERE id = ?
              AND owner_id = ?
            """,
            (
                contest_id,
                user_id,
            ),
        ).fetchone()


def get_required_channels(
    contest_id: int,
):
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT
                channel_id,
                channel_title,
                channel_username,
                invite_link
            FROM required_channels
            WHERE contest_id = ?
            ORDER BY id ASC
            """,
            (contest_id,),
        ).fetchall()


def status_text(
    status: str,
) -> str:
    if status == "scheduled":
        return "⏳ Kutilmoqda"

    if status == "active":
        return "🟢 Faol"

    if status == "finished":
        return "🏁 Tugagan"

    if status == "cancelled":
        return "❌ Bekor qilingan"

    return "❓ Noma'lum"


def format_datetime(
    value,
) -> str:
    if not value:
        return "—"

    value = str(value).strip()

    try:
        parsed = datetime.fromisoformat(
            value
        )

        return parsed.strftime(
            "%d.%m.%Y %H:%M"
        )

    except ValueError:
        return value


def escape_html(
    value,
) -> str:
    if value is None:
        return ""

    value = str(value)

    return (
        value
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def format_contest_text(
    contest,
) -> str:
    participant_count = get_participant_count(
        contest["id"]
    )

    channel_title = (
        contest["channel_title"]
        or contest["channel_username"]
        or "Noma'lum kanal"
    )

    channel_title = escape_html(
        channel_title
    )

    button_text = escape_html(
        contest["button_text"]
        or "🎟 Ishtirok etish"
    )

    post_text = (
        contest["post_text"]
        or ""
    )

    if len(post_text) > 300:
        post_text = (
            post_text[:300]
            + "..."
        )

    post_text = escape_html(
        post_text
    )

    text = (
        f"🎉 <b>Konkurs #{contest['id']}</b>\n\n"
        f"📊 Holati: "
        f"<b>{status_text(contest['status'])}</b>\n"
        f"📢 Kanal: "
        f"<b>{channel_title}</b>\n"
        f"👥 Ishtirokchilar: "
        f"<b>{participant_count}</b>\n"
        f"🏆 G‘oliblar: "
        f"<b>{contest['winners_count']}</b>\n"
        f"🎟 Tugma: "
        f"<b>{button_text}</b>\n\n"
    )

    if contest["start_at"]:
        text += (
            "🟢 Boshlanishi: "
            f"<b>{format_datetime(contest['start_at'])}</b>\n"
        )

    if contest["end_type"] == "time":

        if contest["end_at"]:
            text += (
                "🔴 Tugash vaqti: "
                f"<b>{format_datetime(contest['end_at'])}</b>\n"
            )

    elif contest["end_type"] == "participants":

        limit = contest["participant_limit"]

        text += (
            "👥 Tugash limiti: "
            f"<b>{limit} ta ishtirokchi</b>\n"
        )

    if post_text:
        text += (
            "\n📝 <b>Post:</b>\n"
            f"{post_text}"
        )

    return text


async def show_my_contests(
    message: Message,
) -> None:
    contests = get_user_contests(
        message.from_user.id
    )

    if not contests:
        await message.answer(
            "📋 <b>Konkurslarim</b>\n\n"
            "Sizda hozircha hech qanday "
            "konkurs yo‘q.\n\n"
            "➕ Konkurs yaratish tugmasi orqali "
            "yangi konkurs yaratishingiz mumkin.",
            parse_mode=ParseMode.HTML,
        )
        return

    await message.answer(
        "📋 <b>Konkurslarim</b>\n\n"
        "Kerakli konkursni tanlang:",
        reply_markup=my_contests_keyboard(
            contests,
            page=0,
        ),
        parse_mode=ParseMode.HTML,
    )


@router.message(
    lambda message:
        message.text == "📋 Konkurslarim"
)
async def my_contests_handler(
    message: Message,
) -> None:
    await show_my_contests(
        message
    )


@router.callback_query(
    lambda callback:
        callback.data
        and callback.data.startswith(
            "my_contests_page:"
        )
)
async def my_contests_page_handler(
    callback: CallbackQuery,
) -> None:
    try:
        page = int(
            callback.data.split(
                ":",
                1,
            )[1]
        )

    except (ValueError, IndexError):
        await callback.answer(
            "❌ Sahifa noto‘g‘ri",
            show_alert=True,
        )
        return

    contests = get_user_contests(
        callback.from_user.id
    )

    if not contests:
        await callback.answer(
            "❌ Konkurslar topilmadi",
            show_alert=True,
        )
        return

    await callback.answer()

    await callback.message.edit_reply_markup(
        reply_markup=my_contests_keyboard(
            contests,
            page=page,
        )
    )


@router.callback_query(
    lambda callback:
        callback.data
        == "my_contests_refresh"
)
async def my_contests_refresh_handler(
    callback: CallbackQuery,
) -> None:
    contests = get_user_contests(
        callback.from_user.id
    )

    await callback.answer(
        "🔄 Yangilandi"
    )

    if not contests:
        await callback.message.edit_text(
            "📋 <b>Konkurslarim</b>\n\n"
            "Sizda hozircha hech qanday "
            "konkurs yo‘q.",
            parse_mode=ParseMode.HTML,
        )
        return

    await callback.message.edit_text(
        "📋 <b>Konkurslarim</b>\n\n"
        "Kerakli konkursni tanlang:",
        reply_markup=my_contests_keyboard(
            contests,
            page=0,
        ),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(
    lambda callback:
        callback.data
        == "my_contests_back"
)
async def my_contests_back_handler(
    callback: CallbackQuery,
) -> None:
    contests = get_user_contests(
        callback.from_user.id
    )

    await callback.answer()

    if not contests:
        await callback.message.edit_text(
            "📋 <b>Konkurslarim</b>\n\n"
            "Sizda hozircha hech qanday "
            "konkurs yo‘q.",
            parse_mode=ParseMode.HTML,
        )
        return

    await callback.message.edit_text(
        "📋 <b>Konkurslarim</b>\n\n"
        "Kerakli konkursni tanlang:",
        reply_markup=my_contests_keyboard(
            contests,
            page=0,
        ),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(
    lambda callback:
        callback.data
        and callback.data.startswith(
            "my_contest:"
        )
)
async def my_contest_handler(
    callback: CallbackQuery,
) -> None:
    try:
        contest_id = int(
            callback.data.split(
                ":",
                1,
            )[1]
        )

    except (ValueError, IndexError):
        await callback.answer(
            "❌ Noto‘g‘ri konkurs",
            show_alert=True,
        )
        return

    contest = get_owned_contest(
        telegram_user_id=callback.from_user.id,
        contest_id=contest_id,
    )

    if contest is None:
        await callback.answer(
            "❌ Bu konkurs sizga tegishli emas",
            show_alert=True,
        )
        return

    can_cancel = contest["status"] in (
        "scheduled",
        "active",
    )

    can_finish = (
        contest["status"]
        == "active"
    )

    await callback.answer()

    await callback.message.edit_text(
        format_contest_text(
            contest
        ),
        reply_markup=contest_management_keyboard(
            contest_id=contest_id,
            can_cancel=can_cancel,
            can_finish=can_finish,
        ),
        parse_mode=ParseMode.HTML,
    )


# =========================================================
# EXISTING CONTEST EDIT
# =========================================================

@router.callback_query(
    lambda callback:
        callback.data
        and callback.data.startswith(
            "edit_existing:"
        )
)
async def edit_existing_contest_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    try:
        contest_id = int(
            callback.data.split(
                ":",
                1,
            )[1]
        )

    except (ValueError, IndexError):
        await callback.answer(
            "❌ Noto‘g‘ri konkurs",
            show_alert=True,
        )
        return

    contest = get_owned_contest(
        telegram_user_id=callback.from_user.id,
        contest_id=contest_id,
    )

    if contest is None:
        await callback.answer(
            "❌ Bu konkurs sizga tegishli emas",
            show_alert=True,
        )
        return

    if contest["status"] not in (
        "scheduled",
        "active",
    ):
        await callback.answer(
            "❌ Tugagan yoki bekor qilingan "
            "konkursni tahrirlab bo‘lmaydi",
            show_alert=True,
        )
        return

    required_channels = get_required_channels(
        contest_id
    )

    await state.clear()

    await state.update_data(
        editing_contest_id=contest_id,
        editing_contest_status=contest[
            "status"
        ],

        channel_id=contest[
            "channel_id"
        ],
        channel_title=contest[
            "channel_title"
        ],
        channel_username=contest[
            "channel_username"
        ],
        channel_message_id=contest[
            "channel_message_id"
        ],

        post_type=contest[
            "post_type"
        ],
        post_text=contest[
            "post_text"
        ],
        post_file_id=contest[
            "post_file_id"
        ],

        start_at=contest[
            "start_at"
        ],

        end_type=contest[
            "end_type"
        ],
        end_at=contest[
            "end_at"
        ],
        participant_limit=contest[
            "participant_limit"
        ],

        winners_count=contest[
            "winners_count"
        ],

        button_text=contest[
            "button_text"
        ],

        required_channels=[
            dict(channel)
            for channel in required_channels
        ],
    )

    await state.set_state(
        ContestCreateStates.editing_menu
    )

    await callback.answer()

    if contest["status"] == "active":
        message = (
            f"✏️ <b>Konkurs #{contest_id}</b>\n\n"
            "Konkurs hozir faol.\n\n"
            "📝 Post\n"
            "📋 Obuna kanallari\n"
            "🔴 Tugash sharti\n"
            "🏆 G‘oliblar\n"
            "🎟 Tugma\n\n"
            "⚠️ Kanal va boshlanish vaqtini "
            "faol konkursda o‘zgartirib bo‘lmaydi."
        )

    else:
        message = (
            f"✏️ <b>Konkurs #{contest_id}</b>\n\n"
            "Qaysi qismni o‘zgartirmoqchisiz?"
        )

    await callback.message.edit_text(
        message,
        reply_markup=edit_menu_keyboard(),
        parse_mode=ParseMode.HTML,
    )


# =========================================================
# FINISH
# =========================================================

@router.callback_query(
    lambda callback:
        callback.data
        and callback.data.startswith(
            "finish_contest:"
        )
)
async def finish_contest_handler(
    callback: CallbackQuery,
) -> None:
    try:
        contest_id = int(
            callback.data.split(
                ":",
                1,
            )[1]
        )

    except (ValueError, IndexError):
        await callback.answer(
            "❌ Noto‘g‘ri konkurs",
            show_alert=True,
        )
        return

    contest = get_owned_contest(
        telegram_user_id=callback.from_user.id,
        contest_id=contest_id,
    )

    if contest is None:
        await callback.answer(
            "❌ Bu konkurs sizga tegishli emas",
            show_alert=True,
        )
        return

    if contest["status"] != "active":
        await callback.answer(
            "❌ Faqat faol konkursni tugatish mumkin",
            show_alert=True,
        )
        return

    await callback.answer()

    await callback.message.edit_text(
        "⚠️ <b>Konkursni hozir tugatasizmi?</b>\n\n"
        f"🎉 Konkurs: <b>#{contest_id}</b>\n\n"
        "Konkurs darhol yakunlanadi va "
        "g‘oliblar avtomatik tanlanadi.",
        reply_markup=finish_confirmation_keyboard(
            contest_id
        ),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(
    lambda callback:
        callback.data
        and callback.data.startswith(
            "finish_confirm:"
        )
)
async def finish_confirm_handler(
    callback: CallbackQuery,
) -> None:
    try:
        contest_id = int(
            callback.data.split(
                ":",
                1,
            )[1]
        )

    except (ValueError, IndexError):
        await callback.answer(
            "❌ Noto‘g‘ri konkurs",
            show_alert=True,
        )
        return

    contest = get_owned_contest(
        telegram_user_id=callback.from_user.id,
        contest_id=contest_id,
    )

    if contest is None:
        await callback.answer(
            "❌ Bu konkurs sizga tegishli emas",
            show_alert=True,
        )
        return

    if contest["status"] != "active":
        await callback.answer(
            "❌ Konkurs allaqachon yakunlangan",
            show_alert=True,
        )
        return

    await callback.answer(
        "🏁 Konkurs tugatilmoqda..."
    )

    await finish_contest_job(
        bot=callback.bot,
        contest_id=contest_id,
    )

    await callback.message.edit_text(
        f"🏁 <b>Konkurs #{contest_id}</b>\n\n"
        "Konkurs muvaffaqiyatli yakunlandi.\n\n"
        "🏆 G‘oliblar avtomatik tanlandi.\n"
        "📢 Natijalar kanalga yuborildi.\n"
        "🤖 Kerakli xabarlar foydalanuvchilarga yuborildi.",
        reply_markup=contest_management_keyboard(
            contest_id=contest_id,
            can_cancel=False,
            can_finish=False,
        ),
        parse_mode=ParseMode.HTML,
    )


# =========================================================
# CANCEL
# =========================================================

@router.callback_query(
    lambda callback:
        callback.data
        and callback.data.startswith(
            "cancel_contest:"
        )
)
async def cancel_contest_handler(
    callback: CallbackQuery,
) -> None:
    try:
        contest_id = int(
            callback.data.split(
                ":",
                1,
            )[1]
        )

    except (ValueError, IndexError):
        await callback.answer(
            "❌ Noto‘g‘ri konkurs",
            show_alert=True,
        )
        return

    contest = get_owned_contest(
        telegram_user_id=callback.from_user.id,
        contest_id=contest_id,
    )

    if contest is None:
        await callback.answer(
            "❌ Bu konkurs sizga tegishli emas",
            show_alert=True,
        )
        return

    if contest["status"] not in (
        "scheduled",
        "active",
    ):
        await callback.answer(
            "❌ Bu konkursni bekor qilib bo‘lmaydi",
            show_alert=True,
        )
        return

    await callback.answer()

    await callback.message.edit_text(
        "⚠️ <b>Konkursni bekor qilasizmi?</b>\n\n"
        f"Konkurs: <b>#{contest_id}</b>\n\n"
        "Bekor qilingandan keyin yangi "
        "ishtirokchilar qo‘shila olmaydi.",
        reply_markup=cancel_confirmation_keyboard(
            contest_id
        ),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(
    lambda callback:
        callback.data
        and callback.data.startswith(
            "cancel_confirm:"
        )
)
async def cancel_confirm_handler(
    callback: CallbackQuery,
) -> None:
    try:
        contest_id = int(
            callback.data.split(
                ":",
                1,
            )[1]
        )

    except (ValueError, IndexError):
        await callback.answer(
            "❌ Noto‘g‘ri konkurs",
            show_alert=True,
        )
        return

    contest = get_owned_contest(
        telegram_user_id=callback.from_user.id,
        contest_id=contest_id,
    )

    if contest is None:
        await callback.answer(
            "❌ Bu konkurs sizga tegishli emas",
            show_alert=True,
        )
        return

    if contest["status"] not in (
        "scheduled",
        "active",
    ):
        await callback.answer(
            "❌ Konkurs allaqachon yakunlangan",
            show_alert=True,
        )
        return

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE contests
            SET status = 'cancelled'
            WHERE id = ?
            """,
            (contest_id,),
        )

    await callback.answer(
        "Konkurs bekor qilindi"
    )

    await callback.message.edit_text(
        f"❌ <b>Konkurs #{contest_id}</b>\n\n"
        "Konkurs muvaffaqiyatli bekor qilindi.",
        reply_markup=contest_management_keyboard(
            contest_id=contest_id,
            can_cancel=False,
            can_finish=False,
        ),
        parse_mode=ParseMode.HTML,
    )