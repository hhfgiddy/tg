from datetime import datetime
from html import escape
from typing import Optional

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

from bot.database.db import get_connection
from bot.database.participants import get_participant_count
from bot.database.winners import select_winners
from bot.keyboards.contest import participation_keyboard


scheduler = AsyncIOScheduler()


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


def get_contest_owner_telegram_id(
    contest_id: int,
) -> Optional[int]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT u.telegram_user_id
            FROM contests c
            JOIN users u
                ON u.id = c.owner_id
            WHERE c.id = ?
            """,
            (contest_id,),
        ).fetchone()

        if row is None:
            return None

        return int(row["telegram_user_id"])


def mark_contest_active(contest_id: int) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE contests
            SET status = 'active'
            WHERE id = ?
            """,
            (contest_id,),
        )


def mark_contest_finished(contest_id: int) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE contests
            SET status = 'finished'
            WHERE id = ?
            """,
            (contest_id,),
        )


async def send_contest_to_channel(
    bot: Bot,
    contest_id: int,
) -> None:
    contest = get_contest(contest_id)

    if contest is None:
        return

    if contest["status"] not in ("scheduled", "active"):
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

    channel_id = contest["channel_id"]
    post_type = contest["post_type"]
    post_text = contest["post_text"] or ""
    file_id = contest["post_file_id"]

    sent_message = None

    if post_type == "text":
        sent_message = await bot.send_message(
            chat_id=channel_id,
            text=post_text,
            reply_markup=keyboard,
        )

    elif post_type == "photo":
        sent_message = await bot.send_photo(
            chat_id=channel_id,
            photo=file_id,
            caption=post_text,
            reply_markup=keyboard,
        )

    elif post_type == "video":
        sent_message = await bot.send_video(
            chat_id=channel_id,
            video=file_id,
            caption=post_text,
            reply_markup=keyboard,
        )

    elif post_type == "document":
        sent_message = await bot.send_document(
            chat_id=channel_id,
            document=file_id,
            caption=post_text,
            reply_markup=keyboard,
        )

    elif post_type == "animation":
        sent_message = await bot.send_animation(
            chat_id=channel_id,
            animation=file_id,
            caption=post_text,
            reply_markup=keyboard,
        )

    elif post_type == "audio":
        sent_message = await bot.send_audio(
            chat_id=channel_id,
            audio=file_id,
            reply_markup=keyboard,
        )

    else:
        return

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE contests
            SET
                channel_message_id = ?,
                status = 'active'
            WHERE id = ?
            """,
            (
                sent_message.message_id,
                contest_id,
            ),
        )


def get_clean_name(winner: dict) -> str:
    first_name = winner.get("first_name")

    if not first_name:
        return "G‘olib"

    cleaned = str(first_name).strip()

    if not cleaned:
        return "G‘olib"

    visible_characters = [
        char
        for char in cleaned
        if char.isalnum()
    ]

    if not visible_characters:
        return "G‘olib"

    return cleaned


def format_winner_name(winner: dict) -> str:
    """
    Username bor:
    K o 1 z y X (@Ko1zyX)

    Username yo‘q:
    K o 1 z y X

    Ism va username ikkalasi ham bosilganda
    bir xil Telegram profilini ochadi.
    """

    first_name = escape(
        get_clean_name(winner)
    )

    username = winner.get("username")

    if username:
        clean_username = (
            str(username)
            .strip()
            .lstrip("@")
        )

        if clean_username:
            clean_username = escape(
                clean_username
            )

            return (
                f'<a href="tg://user?id='
                f'{winner["telegram_user_id"]}">'
                f'{first_name}'
                f'</a> '
                f'('
                f'<a href="tg://user?id='
                f'{winner["telegram_user_id"]}">'
                f'@{clean_username}'
                f'</a>'
                f')'
            )

    return (
        f'<a href="tg://user?id='
        f'{winner["telegram_user_id"]}">'
        f'{first_name}'
        f'</a>'
    )


def get_place_text(place: int) -> str:
    if place == 1:
        return "🥇"

    if place == 2:
        return "🥈"

    if place == 3:
        return "🥉"

    return "🏆"


async def send_winner_private_message(
    bot: Bot,
    contest_id: int,
    winner: dict,
    place: int,
) -> None:
    contest = get_contest(contest_id)

    if contest is None:
        return

    text = (
        "🎉 <b>TABRIKLAYMIZ!</b>\n\n"
        "Siz konkursda g‘olib bo‘ldingiz! 🏆\n\n"
        f"{get_place_text(place)} "
        f"<b>O‘rin:</b> {place}\n"
        f"🎁 <b>Konkurs:</b> #{contest_id}\n\n"
        "G‘alabangiz muborak! 🎊\n\n"
        "🎁 <b>Mukofotingiz tez orada "
        "sizga yetkaziladi.</b>"
    )

    try:
        await bot.send_message(
            chat_id=winner["telegram_user_id"],
            text=text,
            parse_mode=ParseMode.HTML,
        )

    except TelegramForbiddenError:
        print(
            "G‘olib botni bloklagan: "
            f"{winner['telegram_user_id']}"
        )

    except TelegramBadRequest as error:
        print(
            "G‘olibga xabar yuborilmadi "
            f"{winner['telegram_user_id']}: {error}"
        )

    except Exception as error:
        print(
            "G‘olibga xabar yuborishda xato: "
            f"{error}"
        )


async def send_winners_post(
    bot: Bot,
    contest_id: int,
) -> None:
    contest = get_contest(contest_id)

    if contest is None:
        return

    participant_count = get_participant_count(
        contest_id
    )

    winners = select_winners(
        contest_id=contest_id,
        winners_count=contest["winners_count"],
    )

    if not winners:
        no_winner_text = (
            "🏁 <b>KONKURS YAKUNLANDI!</b>\n\n"
            "😔 Afsuski, konkursda hech kim "
            "ishtirok etmadi."
        )

        try:
            await bot.send_message(
                chat_id=contest["channel_id"],
                text=no_winner_text,
                parse_mode=ParseMode.HTML,
            )

        except Exception as error:
            print(
                "Kanalga yakuniy xabar yuborilmadi: "
                f"{error}"
            )

        owner_id = get_contest_owner_telegram_id(
            contest_id
        )

        if owner_id:
            owner_text = (
                f"🏁 <b>Konkurs #{contest_id} "
                f"yakunlandi!</b>\n\n"
                f"👥 <b>Ishtirokchilar:</b> "
                f"{participant_count}\n"
                "🏆 <b>G‘oliblar:</b> 0\n\n"
                "😔 Afsuski, konkursda hech kim "
                "ishtirok etmadi."
            )

            try:
                await bot.send_message(
                    chat_id=owner_id,
                    text=owner_text,
                    parse_mode=ParseMode.HTML,
                )

            except Exception as error:
                print(
                    "Konkurs egasiga xabar yuborilmadi: "
                    f"{error}"
                )

        return

    channel_lines = [
        "🏆 <b>KONKURS YAKUNLANDI!</b>",
        "",
        "🎉 <b>G‘oliblar:</b>",
        "",
    ]

    for index, winner in enumerate(
        winners,
        start=1,
    ):
        winner_name = format_winner_name(
            winner
        )

        channel_lines.append(
            f"{get_place_text(index)} "
            f"{winner_name}"
        )

    channel_lines.extend(
        [
            "",
            "🎊 Barcha g‘oliblarni tabriklaymiz!",
        ]
    )

    channel_text = "\n".join(
        channel_lines
    )

    try:
        await bot.send_message(
            chat_id=contest["channel_id"],
            text=channel_text,
            parse_mode=ParseMode.HTML,
        )

    except Exception as error:
        print(
            "Kanalga g‘oliblar xabari "
            f"yuborilmadi: {error}"
        )

    owner_id = get_contest_owner_telegram_id(
        contest_id
    )

    if owner_id:
        owner_lines = [
            f"🏆 <b>Sizning konkursingiz "
            f"#{contest_id} yakunlandi!</b>",
            "",
            f"👥 <b>Ishtirokchilar:</b> "
            f"{participant_count}",
            f"🏆 <b>G‘oliblar soni:</b> "
            f"{len(winners)}",
            "",
            "🎉 <b>G‘oliblar:</b>",
            "",
        ]

        for index, winner in enumerate(
            winners,
            start=1,
        ):
            winner_name = format_winner_name(
                winner
            )

            owner_lines.append(
                f"{get_place_text(index)} "
                f"{winner_name}"
            )

        owner_text = "\n".join(
            owner_lines
        )

        try:
            await bot.send_message(
                chat_id=owner_id,
                text=owner_text,
                parse_mode=ParseMode.HTML,
            )

        except Exception as error:
            print(
                "Konkurs egasiga g‘oliblar xabari "
                f"yuborilmadi: {error}"
            )

    for index, winner in enumerate(
        winners,
        start=1,
    ):
        await send_winner_private_message(
            bot=bot,
            contest_id=contest_id,
            winner=winner,
            place=index,
        )


async def start_contest_job(
    bot: Bot,
    contest_id: int,
) -> None:
    await send_contest_to_channel(
        bot=bot,
        contest_id=contest_id,
    )


async def finish_contest_job(
    bot: Bot,
    contest_id: int,
) -> None:
    contest = get_contest(contest_id)

    if contest is None:
        return

    if contest["status"] != "active":
        return

    mark_contest_finished(contest_id)

    await send_winners_post(
        bot=bot,
        contest_id=contest_id,
    )


def schedule_contest(
    bot: Bot,
    contest_id: int,
    start_at: datetime,
    end_at: Optional[datetime],
) -> None:
    scheduler.add_job(
        start_contest_job,
        trigger=DateTrigger(
            run_date=start_at
        ),
        args=[
            bot,
            contest_id,
        ],
        id=f"contest_start_{contest_id}",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    if end_at is not None:
        scheduler.add_job(
            finish_contest_job,
            trigger=DateTrigger(
                run_date=end_at
            ),
            args=[
                bot,
                contest_id,
            ],
            id=f"contest_end_{contest_id}",
            replace_existing=True,
            misfire_grace_time=3600,
        )


def restore_scheduled_contests(
    bot: Bot,
) -> None:
    now = datetime.now()

    with get_connection() as connection:
        contests = connection.execute(
            """
            SELECT
                id,
                start_at,
                end_at,
                status
            FROM contests
            WHERE status IN ('scheduled', 'active')
            """
        ).fetchall()

    for contest in contests:
        try:
            start_at = datetime.fromisoformat(
                contest["start_at"]
            )

            end_at = None

            if contest["end_at"]:
                end_at = datetime.fromisoformat(
                    contest["end_at"]
                )

            if start_at.tzinfo is None:
                continue

            current_time = now.astimezone(
                start_at.tzinfo
            )

            if start_at > current_time:
                schedule_contest(
                    bot=bot,
                    contest_id=contest["id"],
                    start_at=start_at,
                    end_at=end_at,
                )

            elif contest["status"] == "scheduled":
                scheduler.add_job(
                    start_contest_job,
                    trigger="date",
                    run_date=datetime.now(
                        start_at.tzinfo
                    ),
                    args=[
                        bot,
                        contest["id"],
                    ],
                    id=(
                        f"contest_start_"
                        f"{contest['id']}"
                    ),
                    replace_existing=True,
                )

            elif (
                contest["status"] == "active"
                and end_at is not None
                and end_at
                > now.astimezone(end_at.tzinfo)
            ):
                scheduler.add_job(
                    finish_contest_job,
                    trigger=DateTrigger(
                        run_date=end_at
                    ),
                    args=[
                        bot,
                        contest["id"],
                    ],
                    id=(
                        f"contest_end_"
                        f"{contest['id']}"
                    ),
                    replace_existing=True,
                )

        except Exception:
            continue


def start_scheduler(bot: Bot) -> None:
    restore_scheduled_contests(bot)

    if not scheduler.running:
        scheduler.start()