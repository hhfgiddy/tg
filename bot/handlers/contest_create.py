from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InputMediaAnimation,
    InputMediaAudio,
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
    Message,
)

from apscheduler.jobstores.base import JobLookupError
from apscheduler.triggers.date import DateTrigger

from bot.database.contests import create_contest
from bot.database.db import get_connection
from bot.database.participants import get_participant_count
from bot.keyboards.contest import (
    confirmation_keyboard,
    edit_cancel_keyboard,
    edit_menu_keyboard,
    editing_end_type_keyboard,
    editing_required_channels_keyboard,
    end_type_keyboard,
    required_channels_keyboard,
    start_type_keyboard,
)
from bot.keyboards.my_contests import (
    contest_management_keyboard,
)
from bot.scheduler import (
    finish_contest_job,
    schedule_contest,
    scheduler,
    send_contest_to_channel,
)
from bot.states.contest import ContestCreateStates


router = Router()

TASHKENT_TZ = ZoneInfo("Asia/Tashkent")


# =========================================================
# YORDAMCHI FUNKSIYALAR
# =========================================================

def parse_datetime(
    value: str,
) -> datetime | None:
    formats = [
        "%d.%m.%Y %H:%M",
        "%d-%m-%Y %H:%M",
        "%Y-%m-%d %H:%M",
    ]

    for date_format in formats:
        try:
            return datetime.strptime(
                value,
                date_format,
            ).replace(
                tzinfo=TASHKENT_TZ
            )
        except ValueError:
            continue

    return None


def get_database_contest(
    contest_id: int,
):
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT *
            FROM contests
            WHERE id = ?
            """,
            (contest_id,),
        ).fetchone()


def get_required_channels_from_database(
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


def remove_scheduler_job(
    job_id: str,
) -> None:
    try:
        scheduler.remove_job(
            job_id
        )
    except JobLookupError:
        pass


def schedule_active_end(
    bot,
    contest_id: int,
    end_at: datetime | None,
) -> None:
    job_id = (
        f"contest_end_{contest_id}"
    )

    remove_scheduler_job(
        job_id
    )

    if end_at is None:
        return

    scheduler.add_job(
        finish_contest_job,
        trigger=DateTrigger(
            run_date=end_at
        ),
        args=[
            bot,
            contest_id,
        ],
        id=job_id,
        replace_existing=True,
        misfire_grace_time=3600,
    )


async def update_active_channel_post(
    bot,
    old_contest,
    new_data,
    contest_id: int,
) -> None:
    old_message_id = (
        old_contest["channel_message_id"]
    )

    if not old_message_id:
        return

    old_post_type = (
        old_contest["post_type"]
    )

    new_post_type = (
        new_data.get("post_type")
    )

    old_post_text = (
        old_contest["post_text"]
        or ""
    )

    new_post_text = (
        new_data.get("post_text")
        or ""
    )

    old_file_id = (
        old_contest["post_file_id"]
    )

    new_file_id = (
        new_data.get("post_file_id")
    )

    old_button_text = (
        old_contest["button_text"]
        or "🎟 Ishtirok etish"
    )

    new_button_text = (
        new_data.get("button_text")
        or "🎟 Ishtirok etish"
    )

    post_changed = (
        old_post_type != new_post_type
        or old_post_text != new_post_text
        or old_file_id != new_file_id
        or old_button_text != new_button_text
    )

    if not post_changed:
        return

    bot_info = await bot.get_me()

    participant_count = (
        get_participant_count(
            contest_id
        )
    )

    from bot.keyboards.contest import (
        participation_keyboard,
    )

    keyboard = participation_keyboard(
        contest_id=contest_id,
        bot_username=bot_info.username,
        button_text=new_button_text,
        participant_count=participant_count,
    )

    if (
        old_post_type == "text"
        and new_post_type == "text"
    ):
        try:
            await bot.edit_message_text(
                chat_id=old_contest[
                    "channel_id"
                ],
                message_id=old_message_id,
                text=new_post_text,
                reply_markup=keyboard,
            )
            return

        except TelegramBadRequest:
            pass

    if (
        old_post_type == new_post_type
        and new_post_type != "text"
    ):
        media = None

        if new_post_type == "photo":
            media = InputMediaPhoto(
                media=new_file_id,
                caption=new_post_text,
            )

        elif new_post_type == "video":
            media = InputMediaVideo(
                media=new_file_id,
                caption=new_post_text,
            )

        elif new_post_type == "document":
            media = InputMediaDocument(
                media=new_file_id,
                caption=new_post_text,
            )

        elif new_post_type == "animation":
            media = InputMediaAnimation(
                media=new_file_id,
                caption=new_post_text,
            )

        elif new_post_type == "audio":
            media = InputMediaAudio(
                media=new_file_id,
                caption=new_post_text,
            )

        if media is not None:
            try:
                await bot.edit_message_media(
                    chat_id=old_contest[
                        "channel_id"
                    ],
                    message_id=old_message_id,
                    media=media,
                    reply_markup=keyboard,
                )
                return

            except TelegramBadRequest:
                pass

    try:
        await bot.delete_message(
            chat_id=old_contest[
                "channel_id"
            ],
            message_id=old_message_id,
        )
    except Exception:
        pass

    await send_contest_to_channel(
        bot=bot,
        contest_id=contest_id,
    )


async def update_existing_contest(
    bot,
    contest_id: int,
    data: dict,
) -> None:
    old_contest = get_database_contest(
        contest_id
    )

    if old_contest is None:
        raise ValueError(
            "Konkurs topilmadi."
        )

    old_status = old_contest[
        "status"
    ]

    if (
        old_status == "active"
        and int(data["channel_id"])
        != int(old_contest["channel_id"])
    ):
        raise ValueError(
            "Faol konkursda kanalni almashtirib bo‘lmaydi."
        )

    if (
        old_status == "active"
        and data.get("start_at")
        != old_contest["start_at"]
    ):
        raise ValueError(
            "Faol konkursning boshlanish vaqtini "
            "o‘zgartirib bo‘lmaydi."
        )

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE contests
            SET
                channel_id = ?,
                channel_title = ?,
                channel_username = ?,
                post_type = ?,
                post_text = ?,
                post_file_id = ?,
                start_at = ?,
                end_type = ?,
                end_at = ?,
                participant_limit = ?,
                winners_count = ?,
                button_text = ?
            WHERE id = ?
            """,
            (
                data["channel_id"],
                data.get("channel_title"),
                data.get("channel_username"),
                data["post_type"],
                data.get("post_text"),
                data.get("post_file_id"),
                data["start_at"],
                data["end_type"],
                data.get("end_at"),
                data.get("participant_limit"),
                data["winners_count"],
                data.get(
                    "button_text",
                    "🎟 Ishtirok etish",
                ),
                contest_id,
            ),
        )

        connection.execute(
            """
            DELETE FROM required_channels
            WHERE contest_id = ?
            """,
            (contest_id,),
        )

        required_channels = data.get(
            "required_channels",
            [],
        )

        for channel in required_channels:
            connection.execute(
                """
                INSERT OR IGNORE INTO required_channels (
                    contest_id,
                    channel_id,
                    channel_title,
                    channel_username,
                    invite_link
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    contest_id,
                    channel["channel_id"],
                    channel.get(
                        "channel_title"
                    ),
                    channel.get(
                        "channel_username"
                    ),
                    channel.get(
                        "invite_link"
                    ),
                ),
            )

    start_at = datetime.fromisoformat(
        data["start_at"]
    )

    end_at = None

    if data.get("end_at"):
        end_at = datetime.fromisoformat(
            data["end_at"]
        )

    if old_status == "scheduled":
        remove_scheduler_job(
            f"contest_start_{contest_id}"
        )

        remove_scheduler_job(
            f"contest_end_{contest_id}"
        )

        schedule_contest(
            bot=bot,
            contest_id=contest_id,
            start_at=start_at,
            end_at=end_at,
        )

    elif old_status == "active":
        remove_scheduler_job(
            f"contest_start_{contest_id}"
        )

        schedule_active_end(
            bot=bot,
            contest_id=contest_id,
            end_at=end_at,
        )

    if old_status == "active":
        await update_active_channel_post(
            bot=bot,
            old_contest=old_contest,
            new_data=data,
            contest_id=contest_id,
        )


# =========================================================
# PREVIEW
# =========================================================

async def send_preview(
    message: Message,
    state: FSMContext,
) -> None:
    data = await state.get_data()

    required_channels = data.get(
        "required_channels",
        [],
    )

    if required_channels:
        required_lines = []

        for channel in required_channels:
            username = channel.get(
                "channel_username"
            )

            if username:
                required_lines.append(
                    f"• {channel['channel_title']} "
                    f"({username})"
                )
            else:
                required_lines.append(
                    f"• {channel['channel_title']}"
                )

        required_text = "\n".join(
            required_lines
        )

    else:
        required_text = (
            "• Majburiy obuna yo‘q"
        )

    if data["end_type"] == "time":
        end_datetime = datetime.fromisoformat(
            data["end_at"]
        )

        end_text = end_datetime.strftime(
            "%d.%m.%Y %H:%M"
        )

    else:
        end_text = (
            f"{data['participant_limit']} "
            "ishtirokchiga yetganda"
        )

    if data.get("start_display"):
        start_text = data[
            "start_display"
        ]

    else:
        start_datetime = datetime.fromisoformat(
            data["start_at"]
        )

        start_text = start_datetime.strftime(
            "%d.%m.%Y %H:%M"
        )

    button_text = data.get(
        "button_text",
        "🎟 Ishtirok etish",
    )

    if data.get("editing_contest_id"):
        title = (
            f"✏️ KONKURS #{data['editing_contest_id']} "
            "TAHRIRLASH"
        )
    else:
        title = "📋 KONKURS PREVIEW"

    info_text = (
        f"{title}\n\n"
        f"📢 Kanal: {data['channel_title']}\n\n"
        "📌 Majburiy obuna kanallari:\n"
        f"{required_text}\n\n"
        f"🟢 Boshlanish: {start_text}\n"
        f"🔴 Tugash: {end_text}\n\n"
        f"🏆 G‘oliblar: "
        f"{data['winners_count']} ta\n"
        f"🎟 Tugma: {button_text}\n\n"
        "👇 Konkurs posti quyida ko‘rsatilgan.\n\n"
        "Hammasi to‘g‘rimi?"
    )

    await state.set_state(
        ContestCreateStates.waiting_for_confirmation
    )

    post_type = data["post_type"]
    post_text = (
        data.get("post_text")
        or ""
    )
    file_id = data.get(
        "post_file_id"
    )

    await message.answer(
        info_text
    )

    if post_type == "text":
        await message.answer(
            post_text
        )

    elif post_type == "photo":
        await message.answer_photo(
            photo=file_id,
            caption=post_text,
        )

    elif post_type == "video":
        await message.answer_video(
            video=file_id,
            caption=post_text,
        )

    elif post_type == "document":
        await message.answer_document(
            document=file_id,
            caption=post_text,
        )

    elif post_type == "animation":
        await message.answer_animation(
            animation=file_id,
            caption=post_text,
        )

    elif post_type == "audio":
        await message.answer_audio(
            audio=file_id,
            caption=post_text,
        )

    await message.answer(
        "Yuqoridagi post konkurs kanaliga yuboriladi.\n\n"
        "Tasdiqlaysizmi?",
        reply_markup=confirmation_keyboard(),
    )


# =========================================================
# KONKURS YARATISH
# =========================================================

@router.message(
    F.text == "➕ Konkurs yaratish"
)
async def start_contest_creation(
    message: Message,
    state: FSMContext,
) -> None:
    await state.clear()

    await state.set_state(
        ContestCreateStates.waiting_for_channel
    )

    await message.answer(
        "➕ Konkurs yaratishni boshlaymiz.\n\n"
        "1️⃣ Konkurs qaysi kanalga joylashtiriladi?\n\n"
        "Quyidagilardan birini yuboring:\n\n"
        "@kanal_username\n"
        "https://t.me/kanal_username\n"
        "-1001234567890"
    )


@router.message(
    ContestCreateStates.waiting_for_channel
)
async def receive_channel(
    message: Message,
    state: FSMContext,
) -> None:
    if not message.text:
        await message.answer(
            "❌ Kanal username yoki ID yuboring."
        )
        return

    channel_input = (
        message.text.strip()
    )

    if channel_input.startswith("@"):
        chat_identifier = channel_input

    elif channel_input.startswith(
        "https://t.me/"
    ):
        username = (
            channel_input
            .removeprefix(
                "https://t.me/"
            )
            .strip("/")
            .split("?")[0]
        )

        if not username:
            await message.answer(
                "❌ Telegram kanal havolasi noto‘g‘ri."
            )
            return

        chat_identifier = (
            f"@{username}"
        )

    elif channel_input.startswith("-100"):
        try:
            chat_identifier = int(
                channel_input
            )
        except ValueError:
            await message.answer(
                "❌ Kanal ID noto‘g‘ri."
            )
            return

    else:
        await message.answer(
            "❌ Kanalni quyidagilardan birida yuboring:\n\n"
            "@kanal_username\n"
            "https://t.me/kanal_username\n"
            "-1001234567890"
        )
        return

    try:
        chat = await message.bot.get_chat(
            chat_identifier
        )

    except Exception:
        await message.answer(
            "❌ Kanal topilmadi yoki bot kanalni ko‘ra olmayapti."
        )
        return

    if chat.type != "channel":
        await message.answer(
            "❌ Bu Telegram kanali emas."
        )
        return

    try:
        bot_member = await message.bot.get_chat_member(
            chat_id=chat.id,
            user_id=message.bot.id,
        )

    except Exception:
        await message.answer(
            "❌ Botning kanal huquqlarini tekshirib bo‘lmadi."
        )
        return

    if bot_member.status != "administrator":
        await message.answer(
            "❌ Bot ushbu kanalda administrator emas."
        )
        return

    if not getattr(
        bot_member,
        "can_post_messages",
        False,
    ):
        await message.answer(
            "❌ Botda post yuborish huquqi yo‘q."
        )
        return

    await state.update_data(
        channel_id=chat.id,
        channel_title=chat.title,
        channel_username=getattr(
            chat,
            "username",
            None,
        ),
    )

    await state.set_state(
        ContestCreateStates.waiting_for_post
    )

    await message.answer(
        "✅ Kanal tekshirildi!\n\n"
        f"📢 {chat.title}\n\n"
        "2️⃣ Endi konkurs postini yuboring.\n\n"
        "📝 Matn\n"
        "🖼 Foto + matn\n"
        "🎬 Video + matn\n"
        "📎 Telegram media"
    )


@router.message(
    ContestCreateStates.waiting_for_post
)
async def receive_contest_post(
    message: Message,
    state: FSMContext,
) -> None:
    if message.text:
        post_type = "text"
        text = message.text
        file_id = None

    elif message.photo:
        post_type = "photo"
        text = message.caption or ""
        file_id = message.photo[-1].file_id

    elif message.video:
        post_type = "video"
        text = message.caption or ""
        file_id = message.video.file_id

    elif message.document:
        post_type = "document"
        text = message.caption or ""
        file_id = message.document.file_id

    elif message.animation:
        post_type = "animation"
        text = message.caption or ""
        file_id = message.animation.file_id

    elif message.audio:
        post_type = "audio"
        text = message.caption or ""
        file_id = message.audio.file_id

    else:
        await message.answer(
            "❌ Bu media turi qo‘llab-quvvatlanmaydi."
        )
        return

    if not text and not file_id:
        await message.answer(
            "❌ Konkurs posti bo‘sh bo‘lishi mumkin emas."
        )
        return

    await state.update_data(
        post_type=post_type,
        post_text=text,
        post_file_id=file_id,
        required_channels=[],
    )

    await state.set_state(
        ContestCreateStates.waiting_for_required_channel
    )

    await message.answer(
        "✅ Konkurs posti qabul qilindi!\n\n"
        "3️⃣ Majburiy obuna kanallarini qo‘shamiz.\n\n"
        "Kanalni quyidagicha yuboring:\n\n"
        "@kanal_username\n"
        "https://t.me/kanal_username\n"
        "-1001234567890\n\n"
        "Agar majburiy obuna kerak bo‘lmasa:\n"
        "⏭ O‘tkazib yuborish tugmasini bosing.",
        reply_markup=required_channels_keyboard(),
    )


# =========================================================
# MAJBURIY OBUNA
# =========================================================

@router.message(
    ContestCreateStates.waiting_for_required_channel
)
async def receive_required_channel(
    message: Message,
    state: FSMContext,
) -> None:
    if not message.text:
        await message.answer(
            "❌ Kanal username yoki ID yuboring."
        )
        return

    channel_input = (
        message.text.strip()
    )

    if channel_input.startswith("@"):
        chat_identifier = channel_input

    elif channel_input.startswith(
        "https://t.me/"
    ):
        username = (
            channel_input
            .removeprefix(
                "https://t.me/"
            )
            .strip("/")
            .split("?")[0]
        )

        if not username:
            await message.answer(
                "❌ Havola noto‘g‘ri."
            )
            return

        chat_identifier = (
            f"@{username}"
        )

    elif channel_input.startswith("-100"):
        try:
            chat_identifier = int(
                channel_input
            )
        except ValueError:
            await message.answer(
                "❌ Kanal ID noto‘g‘ri."
            )
            return

    else:
        await message.answer(
            "❌ Kanalni quyidagicha yuboring:\n\n"
            "@kanal_username\n"
            "https://t.me/kanal_username\n"
            "-1001234567890"
        )
        return

    try:
        chat = await message.bot.get_chat(
            chat_identifier
        )

    except Exception:
        await message.answer(
            "❌ Kanal topilmadi."
        )
        return

    if chat.type != "channel":
        await message.answer(
            "❌ Bu Telegram kanali emas."
        )
        return

    try:
        bot_member = await message.bot.get_chat_member(
            chat_id=chat.id,
            user_id=message.bot.id,
        )

    except Exception:
        await message.answer(
            "❌ Botning huquqlarini tekshirib bo‘lmadi."
        )
        return

    if bot_member.status != "administrator":
        await message.answer(
            "❌ Bot ushbu kanalda administrator emas."
        )
        return

    data = await state.get_data()

    required_channels = data.get(
        "required_channels",
        [],
    )

    if any(
        channel["channel_id"] == chat.id
        for channel in required_channels
    ):
        await message.answer(
            "⚠️ Bu kanal allaqachon qo‘shilgan."
        )
        return

    required_channels.append(
        {
            "channel_id": chat.id,
            "channel_title": chat.title,
            "channel_username": getattr(
                chat,
                "username",
                None,
            ),
        }
    )

    await state.update_data(
        required_channels=required_channels
    )

    await message.answer(
        "✅ Kanal qo‘shildi!\n\n"
        f"📢 {chat.title}\n"
        f"📋 Jami: {len(required_channels)}\n\n"
        "Yana kanal qo‘shishingiz yoki tayyor "
        "bo‘lsangiz tugmani bosishingiz mumkin.",
        reply_markup=required_channels_keyboard(),
    )


@router.callback_query(
    F.data == "required_add"
)
async def required_add_channel(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()

    current_state = await state.get_state()

    if (
        current_state
        == ContestCreateStates.editing_required_channel.state
    ):
        await callback.message.answer(
            "➕ Yana majburiy kanal yuboring:\n\n"
            "@kanal_username\n"
            "https://t.me/kanal_username\n"
            "-1001234567890",
            reply_markup=edit_cancel_keyboard(),
        )
        return

    await callback.message.answer(
        "➕ Yana majburiy kanal yuboring:\n\n"
        "@kanal_username\n"
        "https://t.me/kanal_username\n"
        "-1001234567890"
    )


@router.callback_query(
    F.data == "required_skip"
)
async def required_skip(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()

    await state.update_data(
        required_channels=[]
    )

    await state.set_state(
        ContestCreateStates.waiting_for_end_type
    )

    await callback.message.answer(
        "⏭ Majburiy obuna o‘tkazib yuborildi.\n\n"
        "4️⃣ Konkurs qachon tugaydi?",
        reply_markup=end_type_keyboard(),
    )


@router.callback_query(
    F.data == "required_done"
)
async def required_done(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()

    required_channels = data.get(
        "required_channels",
        [],
    )

    if not required_channels:
        await callback.answer(
            "Avval kanal qo‘shing yoki "
            "⏭ O‘tkazib yuborish tugmasini bosing.",
            show_alert=True,
        )
        return

    await callback.answer()

    await state.set_state(
        ContestCreateStates.waiting_for_end_type
    )

    await callback.message.answer(
        "4️⃣ Konkurs qachon tugaydi?",
        reply_markup=end_type_keyboard(),
    )


# =========================================================
# TUGASH SHARTI
# =========================================================

@router.callback_query(
    F.data == "end_time"
)
async def select_end_time(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()

    await state.update_data(
        end_type="time"
    )

    await state.set_state(
        ContestCreateStates.waiting_for_end_value
    )

    current_state = await state.get_state()

    if (
        current_state
        == ContestCreateStates.editing_end_value.state
    ):
        await callback.message.answer(
            "⏰ Tugash vaqtini yuboring.\n\n"
            "Toshkent vaqti bo‘yicha.\n\n"
            "Format:\n"
            "DD.MM.YYYY HH:MM\n\n"
            "Masalan:\n"
            "30.09.2026 20:00",
            reply_markup=edit_cancel_keyboard(),
        )
        return

    await callback.message.answer(
        "⏰ Tugash vaqtini yuboring.\n\n"
        "Toshkent vaqti bo‘yicha.\n\n"
        "Format:\n"
        "DD.MM.YYYY HH:MM\n\n"
        "Masalan:\n"
        "30.09.2026 20:00"
    )


@router.callback_query(
    F.data == "end_participants"
)
async def select_end_participants(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()

    await state.update_data(
        end_type="participants"
    )

    await state.set_state(
        ContestCreateStates.waiting_for_end_value
    )

    current_state = await state.get_state()

    if (
        current_state
        == ContestCreateStates.editing_end_value.state
    ):
        await callback.message.answer(
            "👥 Konkurs nechta ishtirokchiga yetganda tugaydi?\n\n"
            "Faqat son yuboring.\n\n"
            "Masalan:\n"
            "100",
            reply_markup=edit_cancel_keyboard(),
        )
        return

    await callback.message.answer(
        "👥 Konkurs nechta ishtirokchiga yetganda tugaydi?\n\n"
        "Faqat son yuboring.\n\n"
        "Masalan:\n"
        "100"
    )


@router.message(
    ContestCreateStates.waiting_for_end_value
)
async def receive_end_value(
    message: Message,
    state: FSMContext,
) -> None:
    data = await state.get_data()

    end_type = data.get(
        "end_type"
    )

    if end_type == "time":
        if not message.text:
            await message.answer(
                "❌ Tugash vaqtini matn ko‘rinishida yuboring."
            )
            return

        end_at = parse_datetime(
            message.text.strip()
        )

        if end_at is None:
            await message.answer(
                "❌ Sana formati noto‘g‘ri.\n\n"
                "To‘g‘ri format:\n"
                "30.09.2026 20:00"
            )
            return

        now = datetime.now(
            TASHKENT_TZ
        )

        if end_at <= now:
            await message.answer(
                "❌ Tugash vaqti hozirgi vaqtdan keyin "
                "bo‘lishi kerak."
            )
            return

        await state.update_data(
            end_at=end_at.isoformat(),
            participant_limit=None,
        )

    else:
        if not message.text:
            await message.answer(
                "❌ Ishtirokchilar sonini yuboring."
            )
            return

        try:
            participant_limit = int(
                message.text.strip()
            )
        except ValueError:
            await message.answer(
                "❌ Faqat butun son yuboring."
            )
            return

        if participant_limit < 1:
            await message.answer(
                "❌ Ishtirokchilar soni kamida 1 bo‘lishi kerak."
            )
            return

        await state.update_data(
            end_at=None,
            participant_limit=participant_limit,
        )

    await state.set_state(
        ContestCreateStates.waiting_for_winners_count
    )

    await message.answer(
        "5️⃣ Nechta g‘olib bo‘ladi?\n\n"
        "Masalan:\n"
        "3"
    )


# =========================================================
# G‘OLIBLAR
# =========================================================

@router.message(
    ContestCreateStates.waiting_for_winners_count
)
async def receive_winners_count(
    message: Message,
    state: FSMContext,
) -> None:
    if not message.text:
        await message.answer(
            "❌ G‘oliblar sonini yuboring."
        )
        return

    try:
        winners_count = int(
            message.text.strip()
        )
    except ValueError:
        await message.answer(
            "❌ Faqat butun son yuboring."
        )
        return

    if winners_count < 1:
        await message.answer(
            "❌ G‘oliblar soni kamida 1 bo‘lishi kerak."
        )
        return

    await state.update_data(
        winners_count=winners_count
    )

    await state.set_state(
        ContestCreateStates.waiting_for_button_text
    )

    await message.answer(
        "6️⃣ Ishtirok etish tugmasida qanday yozuv bo‘lsin?\n\n"
        "Masalan:\n"
        "🎟 Ishtirok etish\n\n"
        "Standart tugma uchun:\n"
        "default"
    )


# =========================================================
# TUGMA MATNI
# =========================================================

@router.message(
    ContestCreateStates.waiting_for_button_text
)
async def receive_button_text(
    message: Message,
    state: FSMContext,
) -> None:
    if not message.text:
        await message.answer(
            "❌ Tugma nomini matn ko‘rinishida yuboring."
        )
        return

    button_text = (
        message.text.strip()
    )

    if button_text.lower() == "default":
        button_text = (
            "🎟 Ishtirok etish"
        )

    if len(button_text) > 64:
        await message.answer(
            "❌ Tugma nomi juda uzun.\n\n"
            "64 belgidan oshmasin."
        )
        return

    await state.update_data(
        button_text=button_text
    )

    await state.set_state(
        ContestCreateStates.waiting_for_start_time
    )

    await message.answer(
        "7️⃣ Konkurs qachon boshlansin?",
        reply_markup=start_type_keyboard(),
    )


# =========================================================
# BOSHLANISH
# =========================================================

@router.callback_query(
    F.data == "start_now",
    ContestCreateStates.waiting_for_start_time,
)
async def start_now(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    now = datetime.now(
        TASHKENT_TZ
    )

    data = await state.get_data()

    if data.get("end_type") == "time":
        end_at = datetime.fromisoformat(
            data["end_at"]
        )

        if end_at <= now:
            await callback.answer(
                "Tugash vaqti allaqachon o‘tib ketgan.",
                show_alert=True,
            )
            return

    await state.update_data(
        start_at=now.isoformat(),
        start_display="Hozir",
    )

    await callback.answer()

    await send_preview(
        callback.message,
        state,
    )


@router.callback_query(
    F.data == "start_later",
    ContestCreateStates.waiting_for_start_time,
)
async def start_later(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()

    await callback.message.answer(
        "📅 Konkurs boshlanish sanasi va vaqtini yuboring.\n\n"
        "Toshkent vaqti bo‘yicha.\n\n"
        "Format:\n"
        "DD.MM.YYYY HH:MM\n\n"
        "Masalan:\n"
        "25.09.2026 18:00"
    )


@router.message(
    ContestCreateStates.waiting_for_start_time
)
async def receive_start_time(
    message: Message,
    state: FSMContext,
) -> None:
    if not message.text:
        await message.answer(
            "❌ Boshlanish vaqtini yuboring."
        )
        return

    start_at = parse_datetime(
        message.text.strip()
    )

    if start_at is None:
        await message.answer(
            "❌ Sana formati noto‘g‘ri.\n\n"
            "To‘g‘ri format:\n"
            "25.09.2026 18:00"
        )
        return

    now = datetime.now(
        TASHKENT_TZ
    )

    if start_at <= now:
        await message.answer(
            "❌ Boshlanish vaqti hozirgi vaqtdan keyin "
            "bo‘lishi kerak."
        )
        return

    data = await state.get_data()

    if data.get("end_type") == "time":
        end_at = datetime.fromisoformat(
            data["end_at"]
        )

        if end_at <= start_at:
            await message.answer(
                "❌ Tugash vaqti boshlanish vaqtidan keyin "
                "bo‘lishi kerak."
            )
            return

    await state.update_data(
        start_at=start_at.isoformat(),
        start_display=start_at.strftime(
            "%d.%m.%Y %H:%M"
        ),
    )

    await send_preview(
        message,
        state,
    )


# =========================================================
# TAHIRLASH MENYUSI
# =========================================================

@router.callback_query(
    F.data == "contest_edit",
    ContestCreateStates.waiting_for_confirmation,
)
async def edit_contest(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()

    await state.set_state(
        ContestCreateStates.editing_menu
    )

    await callback.message.answer(
        "✏️ Tahrirlash\n\n"
        "Qaysi qismini tahrirlamoqchisiz?",
        reply_markup=edit_menu_keyboard(),
    )


# =========================================================
# EDIT CHANNEL
# =========================================================

@router.callback_query(
    F.data == "edit_channel",
    ContestCreateStates.editing_menu,
)
async def edit_channel(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()

    if data.get(
        "editing_contest_status"
    ) == "active":
        await callback.answer(
            "❌ Faol konkursda kanalni "
            "almashtirib bo‘lmaydi.",
            show_alert=True,
        )
        return

    await callback.answer()

    await state.set_state(
        ContestCreateStates.editing_channel
    )

    await callback.message.answer(
        "📢 Yangi konkurs kanalini yuboring.\n\n"
        "@kanal_username\n"
        "https://t.me/kanal_username\n"
        "-1001234567890",
        reply_markup=edit_cancel_keyboard(),
    )


@router.message(
    ContestCreateStates.editing_channel
)
async def save_edited_channel(
    message: Message,
    state: FSMContext,
) -> None:
    if not message.text:
        await message.answer(
            "❌ Kanal username yoki ID yuboring.",
            reply_markup=edit_cancel_keyboard(),
        )
        return

    channel_input = (
        message.text.strip()
    )

    if channel_input.startswith("@"):
        chat_identifier = channel_input

    elif channel_input.startswith(
        "https://t.me/"
    ):
        username = (
            channel_input
            .removeprefix(
                "https://t.me/"
            )
            .strip("/")
            .split("?")[0]
        )

        if not username:
            await message.answer(
                "❌ Havola noto‘g‘ri.",
                reply_markup=edit_cancel_keyboard(),
            )
            return

        chat_identifier = (
            f"@{username}"
        )

    elif channel_input.startswith("-100"):
        try:
            chat_identifier = int(
                channel_input
            )
        except ValueError:
            await message.answer(
                "❌ Kanal ID noto‘g‘ri.",
                reply_markup=edit_cancel_keyboard(),
            )
            return

    else:
        await message.answer(
            "❌ Kanalni to‘g‘ri formatda yuboring.",
            reply_markup=edit_cancel_keyboard(),
        )
        return

    try:
        chat = await message.bot.get_chat(
            chat_identifier
        )

        if chat.type != "channel":
            await message.answer(
                "❌ Bu Telegram kanali emas.",
                reply_markup=edit_cancel_keyboard(),
            )
            return

        bot_member = await message.bot.get_chat_member(
            chat_id=chat.id,
            user_id=message.bot.id,
        )

        if bot_member.status != "administrator":
            await message.answer(
                "❌ Bot ushbu kanalda administrator emas.",
                reply_markup=edit_cancel_keyboard(),
            )
            return

        if not getattr(
            bot_member,
            "can_post_messages",
            False,
        ):
            await message.answer(
                "❌ Botda post yuborish huquqi yo‘q.",
                reply_markup=edit_cancel_keyboard(),
            )
            return

    except Exception:
        await message.answer(
            "❌ Kanal topilmadi yoki botning huquqlari yetarli emas.",
            reply_markup=edit_cancel_keyboard(),
        )
        return

    await state.update_data(
        channel_id=chat.id,
        channel_title=chat.title,
        channel_username=getattr(
            chat,
            "username",
            None,
        ),
    )

    await send_preview(
        message,
        state,
    )


# =========================================================
# EDIT POST
# =========================================================

@router.callback_query(
    F.data == "edit_post",
    ContestCreateStates.editing_menu,
)
async def edit_post(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()

    await state.set_state(
        ContestCreateStates.editing_post
    )

    await callback.message.answer(
        "📝 Yangi konkurs postini yuboring.\n\n"
        "Matn, foto, video yoki boshqa qo‘llab-quvvatlanadigan media yuborishingiz mumkin.",
        reply_markup=edit_cancel_keyboard(),
    )


@router.message(
    ContestCreateStates.editing_post
)
async def save_edited_post(
    message: Message,
    state: FSMContext,
) -> None:
    if message.text:
        post_type = "text"
        text = message.text
        file_id = None

    elif message.photo:
        post_type = "photo"
        text = message.caption or ""
        file_id = message.photo[-1].file_id

    elif message.video:
        post_type = "video"
        text = message.caption or ""
        file_id = message.video.file_id

    elif message.document:
        post_type = "document"
        text = message.caption or ""
        file_id = message.document.file_id

    elif message.animation:
        post_type = "animation"
        text = message.caption or ""
        file_id = message.animation.file_id

    elif message.audio:
        post_type = "audio"
        text = message.caption or ""
        file_id = message.audio.file_id

    else:
        await message.answer(
            "❌ Bu media turi qo‘llab-quvvatlanmaydi.",
            reply_markup=edit_cancel_keyboard(),
        )
        return

    await state.update_data(
        post_type=post_type,
        post_text=text,
        post_file_id=file_id,
    )

    await send_preview(
        message,
        state,
    )


# =========================================================
# EDIT REQUIRED
# =========================================================

@router.callback_query(
    F.data == "edit_required",
    ContestCreateStates.editing_menu,
)
async def edit_required(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()

    await state.set_state(
        ContestCreateStates.editing_required_channel
    )

    await callback.message.answer(
        "📋 Majburiy obuna kanallarini boshqarish.\n\n"
        "Yangi kanal yuboring.\n\n"
        "Agar majburiy obuna kerak bo‘lmasa:\n"
        "⏭ O‘tkazib yuborish tugmasini bosing.",
        reply_markup=editing_required_channels_keyboard(),
    )


@router.callback_query(
    F.data == "required_skip",
    ContestCreateStates.editing_required_channel,
)
async def edit_required_skip(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()

    await state.update_data(
        required_channels=[]
    )

    await send_preview(
        callback.message,
        state,
    )


@router.callback_query(
    F.data == "required_done",
    ContestCreateStates.editing_required_channel,
)
async def edit_required_done(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()

    await send_preview(
        callback.message,
        state,
    )


@router.message(
    ContestCreateStates.editing_required_channel
)
async def receive_edited_required_channel(
    message: Message,
    state: FSMContext,
) -> None:
    if not message.text:
        await message.answer(
            "❌ Kanal username yoki ID yuboring.",
            reply_markup=edit_cancel_keyboard(),
        )
        return

    channel_input = (
        message.text.strip()
    )

    if channel_input.startswith("@"):
        chat_identifier = channel_input

    elif channel_input.startswith(
        "https://t.me/"
    ):
        username = (
            channel_input
            .removeprefix(
                "https://t.me/"
            )
            .strip("/")
            .split("?")[0]
        )

        if not username:
            await message.answer(
                "❌ Havola noto‘g‘ri.",
                reply_markup=edit_cancel_keyboard(),
            )
            return

        chat_identifier = (
            f"@{username}"
        )

    elif channel_input.startswith("-100"):
        try:
            chat_identifier = int(
                channel_input
            )
        except ValueError:
            await message.answer(
                "❌ Kanal ID noto‘g‘ri.",
                reply_markup=edit_cancel_keyboard(),
            )
            return

    else:
        await message.answer(
            "❌ Kanalni to‘g‘ri formatda yuboring.",
            reply_markup=edit_cancel_keyboard(),
        )
        return

    try:
        chat = await message.bot.get_chat(
            chat_identifier
        )

        if chat.type != "channel":
            await message.answer(
                "❌ Bu Telegram kanali emas.",
                reply_markup=edit_cancel_keyboard(),
            )
            return

        bot_member = await message.bot.get_chat_member(
            chat_id=chat.id,
            user_id=message.bot.id,
        )

        if bot_member.status != "administrator":
            await message.answer(
                "❌ Bot ushbu kanalda administrator emas.",
                reply_markup=edit_cancel_keyboard(),
            )
            return

    except Exception:
        await message.answer(
            "❌ Kanal topilmadi yoki bot admin emas.",
            reply_markup=edit_cancel_keyboard(),
        )
        return

    data = await state.get_data()

    required_channels = data.get(
        "required_channels",
        [],
    )

    if any(
        channel["channel_id"] == chat.id
        for channel in required_channels
    ):
        await message.answer(
            "⚠️ Bu kanal allaqachon qo‘shilgan.",
            reply_markup=editing_required_channels_keyboard(),
        )
        return

    required_channels.append(
        {
            "channel_id": chat.id,
            "channel_title": chat.title,
            "channel_username": getattr(
                chat,
                "username",
                None,
            ),
        }
    )

    await state.update_data(
        required_channels=required_channels
    )

    await message.answer(
        "✅ Kanal qo‘shildi!\n\n"
        f"📢 {chat.title}\n"
        f"📋 Jami: {len(required_channels)}",
        reply_markup=editing_required_channels_keyboard(),
    )


# =========================================================
# EDIT END
# =========================================================

@router.callback_query(
    F.data == "edit_end",
    ContestCreateStates.editing_menu,
)
async def edit_end(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()

    await state.set_state(
        ContestCreateStates.editing_end_type
    )

    await callback.message.answer(
        "🔴 Yangi tugash shartini tanlang:",
        reply_markup=editing_end_type_keyboard(),
    )


@router.callback_query(
    F.data == "end_time",
    ContestCreateStates.editing_end_type,
)
async def edit_end_time(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()

    await state.update_data(
        end_type="time"
    )

    await state.set_state(
        ContestCreateStates.editing_end_value
    )

    await callback.message.answer(
        "⏰ Yangi tugash vaqtini yuboring.\n\n"
        "DD.MM.YYYY HH:MM",
        reply_markup=edit_cancel_keyboard(),
    )


@router.callback_query(
    F.data == "end_participants",
    ContestCreateStates.editing_end_type,
)
async def edit_end_participants(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()

    await state.update_data(
        end_type="participants"
    )

    await state.set_state(
        ContestCreateStates.editing_end_value
    )

    await callback.message.answer(
        "👥 Yangi ishtirokchilar limitini yuboring.\n\n"
        "Masalan: 100",
        reply_markup=edit_cancel_keyboard(),
    )


@router.message(
    ContestCreateStates.editing_end_value
)
async def save_edited_end(
    message: Message,
    state: FSMContext,
) -> None:
    if not message.text:
        await message.answer(
            "❌ Qiymatni matn ko‘rinishida yuboring.",
            reply_markup=edit_cancel_keyboard(),
        )
        return

    data = await state.get_data()

    if data.get("end_type") == "time":
        end_at = parse_datetime(
            message.text.strip()
        )

        if end_at is None:
            await message.answer(
                "❌ Sana formati noto‘g‘ri.\n\n"
                "DD.MM.YYYY HH:MM",
                reply_markup=edit_cancel_keyboard(),
            )
            return

        now = datetime.now(
            TASHKENT_TZ
        )

        if end_at <= now:
            await message.answer(
                "❌ Tugash vaqti kelajakda bo‘lishi kerak.",
                reply_markup=edit_cancel_keyboard(),
            )
            return

        start_at = data.get(
            "start_at"
        )

        if start_at:
            start_datetime = datetime.fromisoformat(
                start_at
            )

            if end_at <= start_datetime:
                await message.answer(
                    "❌ Tugash vaqti boshlanishdan keyin bo‘lishi kerak.",
                    reply_markup=edit_cancel_keyboard(),
                )
                return

        await state.update_data(
            end_at=end_at.isoformat(),
            participant_limit=None,
        )

    else:
        try:
            participant_limit = int(
                message.text.strip()
            )
        except ValueError:
            await message.answer(
                "❌ Faqat butun son yuboring.",
                reply_markup=edit_cancel_keyboard(),
            )
            return

        if participant_limit < 1:
            await message.answer(
                "❌ Limit kamida 1 bo‘lishi kerak.",
                reply_markup=edit_cancel_keyboard(),
            )
            return

        await state.update_data(
            end_at=None,
            participant_limit=participant_limit,
        )

    await send_preview(
        message,
        state,
    )


# =========================================================
# EDIT WINNERS
# =========================================================

@router.callback_query(
    F.data == "edit_winners",
    ContestCreateStates.editing_menu,
)
async def edit_winners(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()

    await state.set_state(
        ContestCreateStates.editing_winners_count
    )

    await callback.message.answer(
        "🏆 Yangi g‘oliblar sonini yuboring.\n\n"
        "Masalan: 3",
        reply_markup=edit_cancel_keyboard(),
    )


@router.message(
    ContestCreateStates.editing_winners_count
)
async def save_edited_winners(
    message: Message,
    state: FSMContext,
) -> None:
    if not message.text:
        await message.answer(
            "❌ G‘oliblar sonini yuboring.",
            reply_markup=edit_cancel_keyboard(),
        )
        return

    try:
        winners_count = int(
            message.text.strip()
        )
    except ValueError:
        await message.answer(
            "❌ Faqat butun son yuboring.",
            reply_markup=edit_cancel_keyboard(),
        )
        return

    if winners_count < 1:
        await message.answer(
            "❌ Kamida 1 ta g‘olib bo‘lishi kerak.",
            reply_markup=edit_cancel_keyboard(),
        )
        return

    await state.update_data(
        winners_count=winners_count
    )

    await send_preview(
        message,
        state,
    )


# =========================================================
# EDIT BUTTON
# =========================================================

@router.callback_query(
    F.data == "edit_button",
    ContestCreateStates.editing_menu,
)
async def edit_button(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()

    await state.set_state(
        ContestCreateStates.editing_button_text
    )

    await callback.message.answer(
        "🎟 Yangi tugma nomini yuboring.\n\n"
        "Masalan:\n"
        "🎁 Konkursga qo‘shilish\n\n"
        "Standart uchun:\n"
        "default",
        reply_markup=edit_cancel_keyboard(),
    )


@router.message(
    ContestCreateStates.editing_button_text
)
async def save_edited_button(
    message: Message,
    state: FSMContext,
) -> None:
    if not message.text:
        await message.answer(
            "❌ Tugma nomini yuboring.",
            reply_markup=edit_cancel_keyboard(),
        )
        return

    button_text = (
        message.text.strip()
    )

    if button_text.lower() == "default":
        button_text = (
            "🎟 Ishtirok etish"
        )

    if len(button_text) > 64:
        await message.answer(
            "❌ Tugma nomi 64 belgidan oshmasin.",
            reply_markup=edit_cancel_keyboard(),
        )
        return

    await state.update_data(
        button_text=button_text
    )

    await send_preview(
        message,
        state,
    )


# =========================================================
# EDIT START
# =========================================================

@router.callback_query(
    F.data == "edit_start",
    ContestCreateStates.editing_menu,
)
async def edit_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()

    if data.get(
        "editing_contest_status"
    ) == "active":
        await callback.answer(
            "❌ Faol konkurs allaqachon boshlangan.",
            show_alert=True,
        )
        return

    await callback.answer()

    await state.set_state(
        ContestCreateStates.editing_start_time
    )

    await callback.message.answer(
        "🟢 Yangi boshlanish vaqtini yuboring.\n\n"
        "Format:\n"
        "DD.MM.YYYY HH:MM\n\n"
        "Masalan:\n"
        "25.09.2026 18:00",
        reply_markup=edit_cancel_keyboard(),
    )


@router.message(
    ContestCreateStates.editing_start_time
)
async def save_edited_start(
    message: Message,
    state: FSMContext,
) -> None:
    if not message.text:
        await message.answer(
            "❌ Boshlanish vaqtini yuboring.",
            reply_markup=edit_cancel_keyboard(),
        )
        return

    start_at = parse_datetime(
        message.text.strip()
    )

    if start_at is None:
        await message.answer(
            "❌ Sana formati noto‘g‘ri.",
            reply_markup=edit_cancel_keyboard(),
        )
        return

    now = datetime.now(
        TASHKENT_TZ
    )

    if start_at <= now:
        await message.answer(
            "❌ Boshlanish vaqti kelajakda bo‘lishi kerak.",
            reply_markup=edit_cancel_keyboard(),
        )
        return

    data = await state.get_data()

    if data.get("end_type") == "time":
        end_at = datetime.fromisoformat(
            data["end_at"]
        )

        if end_at <= start_at:
            await message.answer(
                "❌ Tugash vaqti boshlanishdan keyin bo‘lishi kerak.",
                reply_markup=edit_cancel_keyboard(),
            )
            return

    await state.update_data(
        start_at=start_at.isoformat(),
        start_display=start_at.strftime(
            "%d.%m.%Y %H:%M"
        ),
    )

    await send_preview(
        message,
        state,
    )


# =========================================================
# EDIT BACK
# =========================================================

@router.callback_query(
    F.data == "edit_back",
    ContestCreateStates.editing_menu,
)
async def edit_back(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()

    await send_preview(
        callback.message,
        state,
    )


# =========================================================
# TAHIRLASHNI BEKOR QILISH
# =========================================================

@router.callback_query(
    F.data == "edit_cancel",
)
async def edit_cancel(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()

    editing_contest_id = data.get(
        "editing_contest_id"
    )

    if not editing_contest_id:
        await callback.answer(
            "❌ Tahrirlash topilmadi.",
            show_alert=True,
        )
        return

    contest = get_database_contest(
        int(editing_contest_id)
    )

    await state.clear()

    await callback.answer(
        "Tahrirlash bekor qilindi."
    )

    if contest is None:
        await callback.message.edit_text(
            "❌ Konkurs topilmadi."
        )
        return

    can_cancel = contest[
        "status"
    ] in (
        "scheduled",
        "active",
    )

    can_finish = (
        contest["status"]
        == "active"
    )

    await callback.message.edit_text(
        f"❌ <b>Konkurs #{editing_contest_id}</b>\n\n"
        "Tahrirlash bekor qilindi.\n"
        "Konkurs o‘zgartirilmadi.",
        reply_markup=contest_management_keyboard(
            contest_id=int(
                editing_contest_id
            ),
            can_cancel=can_cancel,
            can_finish=can_finish,
        ),
        parse_mode=ParseMode.HTML,
    )


# =========================================================
# TASDIQLASH
# =========================================================

@router.callback_query(
    F.data == "contest_confirm",
    ContestCreateStates.waiting_for_confirmation,
)
async def confirm_contest_creation(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()

    if not data:
        await callback.answer(
            "Konkurs ma’lumotlari topilmadi.",
            show_alert=True,
        )
        return

    editing_contest_id = data.get(
        "editing_contest_id"
    )

    if editing_contest_id:
        try:
            await update_existing_contest(
                bot=callback.bot,
                contest_id=int(
                    editing_contest_id
                ),
                data=data,
            )

        except ValueError as error:
            await callback.answer(
                str(error),
                show_alert=True,
            )
            return

        except Exception as error:
            print(
                "Existing contest update error:",
                error,
            )

            await callback.answer(
                "❌ Konkursni yangilashda xatolik yuz berdi.",
                show_alert=True,
            )
            return

        contest = get_database_contest(
            int(editing_contest_id)
        )

        await state.clear()

        await callback.answer(
            "✅ Konkurs saqlandi!"
        )

        if contest is not None:
            can_cancel = contest[
                "status"
            ] in (
                "scheduled",
                "active",
            )

            can_finish = (
                contest["status"]
                == "active"
            )

            await callback.message.edit_text(
                f"✅ <b>Konkurs #{editing_contest_id}</b>\n\n"
                "Konkurs muvaffaqiyatli yangilandi.\n\n"
                "O‘zgarishlar saqlandi.",
                reply_markup=contest_management_keyboard(
                    contest_id=int(
                        editing_contest_id
                    ),
                    can_cancel=can_cancel,
                    can_finish=can_finish,
                ),
                parse_mode=ParseMode.HTML,
            )

        return

    user = callback.from_user

    with get_connection() as connection:
        owner = connection.execute(
            """
            SELECT id
            FROM users
            WHERE telegram_user_id = ?
            """,
            (user.id,),
        ).fetchone()

    if not owner:
        await callback.answer(
            "Foydalanuvchi topilmadi.",
            show_alert=True,
        )
        return

    contest_id = create_contest(
        owner_id=owner["id"],
        data=data,
    )

    start_at = datetime.fromisoformat(
        data["start_at"]
    )

    end_at = None

    if data.get("end_at"):
        end_at = datetime.fromisoformat(
            data["end_at"]
        )

    try:
        if data.get(
            "start_display"
        ) == "Hozir":

            await send_contest_to_channel(
                bot=callback.bot,
                contest_id=contest_id,
            )

            if end_at is not None:
                schedule_active_end(
                    bot=callback.bot,
                    contest_id=contest_id,
                    end_at=end_at,
                )

            start_result = (
                "🟢 Konkurs hozir boshlandi"
            )

        else:
            schedule_contest(
                bot=callback.bot,
                contest_id=contest_id,
                start_at=start_at,
                end_at=end_at,
            )

            start_result = (
                "🟡 Konkurs rejalashtirildi"
            )

    except Exception:
        with get_connection() as connection:
            connection.execute(
                """
                DELETE FROM contests
                WHERE id = ?
                """,
                (contest_id,),
            )

        await callback.answer(
            "Kanalga yuborishda xatolik yuz berdi.",
            show_alert=True,
        )

        raise

    await state.clear()

    await callback.answer(
        "Konkurs yaratildi!"
    )

    await callback.message.answer(
        "🎉 Konkurs muvaffaqiyatli yaratildi!\n\n"
        f"🆔 Konkurs ID: {contest_id}\n"
        f"📢 Kanal: {data['channel_title']}\n"
        f"🎟 Tugma: {data['button_text']}\n\n"
        f"{start_result}"
    )


# =========================================================
# EXISTING EDIT CANCEL
# =========================================================

@router.callback_query(
    F.data == "contest_cancel",
)
async def cancel_contest_creation(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()

    editing_contest_id = data.get(
        "editing_contest_id"
    )

    if editing_contest_id:
        contest = get_database_contest(
            int(editing_contest_id)
        )

        await state.clear()

        await callback.answer(
            "Tahrirlash bekor qilindi."
        )

        if contest is not None:
            can_cancel = contest[
                "status"
            ] in (
                "scheduled",
                "active",
            )

            can_finish = (
                contest["status"]
                == "active"
            )

            await callback.message.edit_text(
                f"❌ <b>Konkurs #{editing_contest_id}</b>\n\n"
                "Tahrirlash bekor qilindi.\n"
                "Konkurs o‘zgartirilmadi.",
                reply_markup=contest_management_keyboard(
                    contest_id=int(
                        editing_contest_id
                    ),
                    can_cancel=can_cancel,
                    can_finish=can_finish,
                ),
                parse_mode=ParseMode.HTML,
            )

        return

    await state.clear()

    await callback.answer()

    await callback.message.answer(
        "❌ Konkurs yaratish bekor qilindi."
    )