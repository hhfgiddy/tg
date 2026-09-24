from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message

from bot.database.db import get_connection
from bot.database.participants import (
    add_participant,
    get_participant_count,
    is_participant,
)
from bot.keyboards.contest import (
    participation_keyboard,
    subscription_check_keyboard,
)
from bot.scheduler import finish_contest_job

router = Router()


def get_contest(contest_id: int):
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT *
            FROM contests
            WHERE id = ?
            """,
            (contest_id,),
        ).fetchone()


def get_required_channels(contest_id: int):
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT
                id,
                channel_id,
                channel_title,
                channel_username,
                invite_link
            FROM required_channels
            WHERE contest_id = ?
            ORDER BY id
            """,
            (contest_id,),
        ).fetchall()


async def check_subscription(
    bot,
    user_id: int,
    channel_id: int,
) -> bool:
    try:
        member = await bot.get_chat_member(
            chat_id=channel_id,
            user_id=user_id,
        )

        if member.status in {
            "member",
            "administrator",
            "creator",
        }:
            return True

        if (
            member.status == "restricted"
            and getattr(member, "is_member", False)
        ):
            return True

        return False

    except Exception:
        return False


async def update_participation_button(
    bot,
    contest_id: int,
) -> None:
    contest = get_contest(contest_id)

    if contest is None:
        return

    message_id = contest["channel_message_id"]

    if not message_id:
        return

    bot_info = await bot.get_me()

    participant_count = get_participant_count(
        contest_id
    )

    keyboard = participation_keyboard(
        contest_id=contest_id,
        bot_username=bot_info.username,
        button_text=contest["button_text"],
        participant_count=participant_count,
    )

    try:
        await bot.edit_message_reply_markup(
            chat_id=contest["channel_id"],
            message_id=message_id,
            reply_markup=keyboard,
        )

    except TelegramBadRequest:
        pass


async def check_participant_limit(
    bot,
    contest_id: int,
) -> None:
    contest = get_contest(contest_id)

    if contest is None:
        return

    if contest["status"] != "active":
        return

    if contest["end_type"] != "participants":
        return

    participant_limit = contest["participant_limit"]

    if not participant_limit:
        return

    participant_count = get_participant_count(
        contest_id
    )

    if participant_count >= participant_limit:
        await finish_contest_job(
            bot=bot,
            contest_id=contest_id,
        )


async def check_and_join(
    bot,
    user_id: int,
    contest_id: int,
) -> tuple[bool, str, list[dict]]:

    contest = get_contest(contest_id)

    if contest is None:
        return (
            False,
            "❌ Konkurs topilmadi",
            [],
        )

    if contest["status"] != "active":
        return (
            False,
            "❌ Bu konkurs hozir faol emas",
            [],
        )

    if is_participant(
        telegram_user_id=user_id,
        contest_id=contest_id,
    ):
        return (
            False,
            "ℹ️ Siz allaqachon konkursda "
            "ishtirok etyapsiz",
            [],
        )

    channels = get_required_channels(
        contest_id
    )

    not_subscribed = []

    for channel in channels:
        subscribed = await check_subscription(
            bot=bot,
            user_id=user_id,
            channel_id=channel["channel_id"],
        )

        if not subscribed:
            not_subscribed.append(
                {
                    "channel_title": channel[
                        "channel_title"
                    ],
                    "channel_username": channel[
                        "channel_username"
                    ],
                    "invite_link": channel[
                        "invite_link"
                    ],
                }
            )

    if not_subscribed:
        return (
            False,
            "❌ Konkursda ishtirok etish uchun "
            "quyidagi kanallarga obuna bo‘ling:",
            not_subscribed,
        )

    # Limitni oldindan tekshirish
    if contest["end_type"] == "participants":
        participant_limit = contest[
            "participant_limit"
        ]

        if participant_limit:
            current_count = get_participant_count(
                contest_id
            )

            if current_count >= participant_limit:
                return (
                    False,
                    "❌ Konkursdagi ishtirokchilar "
                    "limiti to‘ldi.",
                    [],
                )

    added = add_participant(
        telegram_user_id=user_id,
        contest_id=contest_id,
    )

    if not added:
        return (
            False,
            "ℹ️ Siz allaqachon konkursda "
            "ishtirok etyapsiz",
            [],
        )

    # Tugmadagi participant countni yangilash
    await update_participation_button(
        bot=bot,
        contest_id=contest_id,
    )

    # Limitga yetgan-yetmaganini tekshirish
    await check_participant_limit(
        bot=bot,
        contest_id=contest_id,
    )

    return (
        True,
        "🎉 Siz konkursga muvaffaqiyatli "
        "qo‘shildingiz!",
        [],
    )


async def process_start_participation(
    message: Message,
    contest_id: int,
) -> None:

    user_id = message.from_user.id

    success, text, not_subscribed = (
        await check_and_join(
            bot=message.bot,
            user_id=user_id,
            contest_id=contest_id,
        )
    )

    if not_subscribed:
        await message.answer(
            text,
            reply_markup=subscription_check_keyboard(
                contest_id=contest_id,
                channels=not_subscribed,
            ),
        )
        return

    await message.answer(text)


@router.callback_query(
    lambda callback:
        callback.data
        and callback.data.startswith(
            "contest_check:"
        )
)
async def contest_check_handler(
    callback: CallbackQuery,
) -> None:

    try:
        contest_id = int(
            callback.data.split(":", 1)[1]
        )

    except (ValueError, IndexError):
        await callback.answer(
            "❌ Noto‘g‘ri konkurs",
            show_alert=True,
        )
        return

    user_id = callback.from_user.id

    try:
        await callback.message.delete()

    except TelegramBadRequest:
        pass

    success, text, not_subscribed = (
        await check_and_join(
            bot=callback.bot,
            user_id=user_id,
            contest_id=contest_id,
        )
    )

    await callback.answer()

    if not_subscribed:
        await callback.message.answer(
            text,
            reply_markup=subscription_check_keyboard(
                contest_id=contest_id,
                channels=not_subscribed,
            ),
        )
        return

    await callback.message.answer(text)