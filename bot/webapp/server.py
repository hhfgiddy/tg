import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aiohttp import web
from aiogram import Bot
from aiogram.types import BufferedInputFile
from aiogram.utils.web_app import safe_parse_webapp_init_data

from bot.config import BOT_TOKEN
from bot.database.contests import create_contest
from bot.database.db import get_connection
from bot.database.users import create_or_update_user
from bot.scheduler import schedule_contest, send_contest_to_channel


BASE_DIR = Path(__file__).resolve().parent.parent.parent
WEBAPP_DIR = BASE_DIR / "webapp"

USERNAME_RE = re.compile(
    r"^[A-Za-z0-9_]{5,32}$"
)

MAX_IMAGE_SIZE = 10 * 1024 * 1024


# =========================================
# JSON RESPONSE
# =========================================

def json_response(
    data: dict[str, Any],
    status: int = 200,
) -> web.Response:
    return web.json_response(
        data,
        status=status,
    )


# =========================================
# TELEGRAM WEB APP AUTH
# =========================================

def get_init_data(
    request: web.Request,
) -> str:
    return request.headers.get(
        "X-Telegram-Init-Data",
        "",
    ).strip()


def get_authenticated_user(
    request: web.Request,
) -> dict[str, Any]:
    init_data = get_init_data(request)

    if not init_data:
        raise web.HTTPUnauthorized(
            text=json.dumps(
                {
                    "error": (
                        "Telegram WebApp initData "
                        "topilmadi."
                    )
                },
                ensure_ascii=False,
            ),
            content_type="application/json",
        )

    try:
        parsed = safe_parse_webapp_init_data(
            token=BOT_TOKEN,
            init_data=init_data,
        )
    except ValueError:
        raise web.HTTPUnauthorized(
            text=json.dumps(
                {
                    "error": (
                        "Telegram WebApp sessiyasi "
                        "noto'g'ri yoki eskirgan."
                    )
                },
                ensure_ascii=False,
            ),
            content_type="application/json",
        )

    if parsed.user is None:
        raise web.HTTPUnauthorized(
            text=json.dumps(
                {
                    "error": (
                        "Telegram foydalanuvchisi "
                        "aniqlanmadi."
                    )
                },
                ensure_ascii=False,
            ),
            content_type="application/json",
        )

    user = parsed.user.model_dump()

    create_or_update_user(
        telegram_user_id=user["id"],
        username=user.get("username"),
        first_name=user.get("first_name"),
    )

    return user


# =========================================
# TELEGRAM TARGET NORMALIZER
# =========================================

def normalize_target(
    value: str,
) -> tuple[str, str]:
    raw = str(value or "").strip()

    if not raw:
        raise web.HTTPBadRequest(
            text=json.dumps(
                {
                    "error": (
                        "Telegram kanalini "
                        "kiriting."
                    )
                },
                ensure_ascii=False,
            ),
            content_type="application/json",
        )

    if re.match(
        r"^https?://t\.me/",
        raw,
        re.IGNORECASE,
    ):
        raw = re.sub(
            r"^https?://t\.me/",
            "",
            raw,
            flags=re.IGNORECASE,
        )

        raw = raw.split("/", 1)[0]
        raw = raw.split("?", 1)[0]

    if raw.startswith("@"):
        raw = raw[1:]

    if raw.lstrip("-").isdigit():
        return (
            "id",
            raw,
        )

    if USERNAME_RE.fullmatch(raw):
        return (
            "username",
            f"@{raw}",
        )

    raise web.HTTPBadRequest(
        text=json.dumps(
            {
                "error": (
                    "Telegram kanal formati "
                    "noto'g'ri."
                )
            },
            ensure_ascii=False,
        ),
        content_type="application/json",
    )


# =========================================
# TELEGRAM CHANNEL ERROR
# =========================================

def channel_error(
    message: str,
) -> web.HTTPBadRequest:
    return web.HTTPBadRequest(
        text=json.dumps(
            {
                "error": message,
            },
            ensure_ascii=False,
        ),
        content_type="application/json",
    )


# =========================================
# RESOLVE TELEGRAM CHANNEL
# =========================================

async def resolve_channel(
    bot: Bot,
    value: str,
    user_id: int,
    require_owner: bool,
    require_post_permission: bool,
) -> dict[str, Any]:
    target_type, target_value = normalize_target(
        value
    )

    # -------------------------------------
    # GET CHAT
    # -------------------------------------

    try:
        chat = await bot.get_chat(
            chat_id=target_value
        )
    except Exception:
        raise channel_error(
            "Telegram kanal topilmadi. "
            "Username yoki IDni tekshiring."
        )

    if chat.type != "channel":
        raise channel_error(
            "Kiritilgan Telegram chat "
            "kanal bo'lishi kerak."
        )

    # -------------------------------------
    # CHECK USER OWNER
    # -------------------------------------

    if require_owner:
        try:
            user_member = await bot.get_chat_member(
                chat_id=chat.id,
                user_id=user_id,
            )
        except Exception:
            raise channel_error(
                "Sizning bu kanalga egaligingizni "
                "tekshirib bo'lmadi."
            )

        if user_member.status != "creator":
            raise channel_error(
                "Konkurs o'tkaziladigan kanalning "
                "egasi siz bo'lishingiz kerak."
            )

    # -------------------------------------
    # CHECK BOT ADMIN
    # -------------------------------------

    bot_info = await bot.get_me()

    try:
        bot_member = await bot.get_chat_member(
            chat_id=chat.id,
            user_id=bot_info.id,
        )
    except Exception:
        raise channel_error(
            "Bot bu kanalni tekshira olmadi. "
            "Botni kanalga administrator qilib "
            "qo'ying."
        )

    if bot_member.status not in {
        "administrator",
        "creator",
    }:
        raise channel_error(
            "Bot bu kanalda administrator emas."
        )

    # -------------------------------------
    # CHECK BOT POST PERMISSION
    # -------------------------------------

    if require_post_permission:
        can_post = getattr(
            bot_member,
            "can_post_messages",
            None,
        )

        if (
            bot_member.status == "administrator"
            and can_post is False
        ):
            raise channel_error(
                "Botda kanalga post yuborish "
                "huquqi yo'q."
            )

    # -------------------------------------
    # CHANNEL DATA
    # -------------------------------------

    username = getattr(
        chat,
        "username",
        None,
    )

    return {
        "channel_id": int(chat.id),
        "title": (
            chat.title
            or "Telegram kanali"
        ),
        "username": (
            f"@{username}"
            if username
            else None
        ),
        "display": (
            f"@{username}"
            if username
            else (
                chat.title
                or str(chat.id)
            )
        ),
        "key": (
            f"username:{username.lower()}"
            if username
            else f"id:{chat.id}"
        ),
        "type": target_type,
    }


# =========================================
# ME
# =========================================

async def api_me(
    request: web.Request,
) -> web.Response:
    user = get_authenticated_user(
        request
    )

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                id,
                telegram_user_id,
                username,
                first_name,
                created_at
            FROM users
            WHERE telegram_user_id = ?
            """,
            (user["id"],),
        ).fetchone()

    return json_response(
        {
            "user": (
                dict(row)
                if row
                else user
            )
        }
    )


# =========================================
# RESOLVE TARGET API
# =========================================

async def api_resolve_target(
    request: web.Request,
) -> web.Response:
    user = get_authenticated_user(
        request
    )

    try:
        payload = await request.json()
    except Exception:
        raise web.HTTPBadRequest(
            text=json.dumps(
                {
                    "error": (
                        "JSON ma'lumoti "
                        "noto'g'ri."
                    )
                },
                ensure_ascii=False,
            ),
            content_type="application/json",
        )

    value = payload.get(
        "value",
        "",
    )

    purpose = payload.get(
        "purpose",
        "target",
    )

    # =====================================
    # TARGET
    # =====================================

    if purpose == "target":
        channel = await resolve_channel(
            bot=request.app["bot"],
            value=value,
            user_id=user["id"],
            require_owner=True,
            require_post_permission=True,
        )

    # =====================================
    # REQUIRED CHANNEL
    # =====================================

    elif purpose == "required":
        channel = await resolve_channel(
            bot=request.app["bot"],
            value=value,
            user_id=user["id"],
            require_owner=False,
            require_post_permission=False,
        )

    else:
        raise web.HTTPBadRequest(
            text=json.dumps(
                {
                    "error": (
                        "Kanal maqsadi noto'g'ri."
                    )
                },
                ensure_ascii=False,
            ),
            content_type="application/json",
        )

    return json_response(
        {
            "channel": channel
        }
    )


# =========================================
# DATETIME
# =========================================

def parse_iso_datetime(
    value: str,
) -> datetime:
    try:
        parsed = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )
    except ValueError:
        raise web.HTTPBadRequest(
            text=json.dumps(
                {
                    "error": (
                        "Sana/vaqt formati "
                        "noto'g'ri."
                    )
                },
                ensure_ascii=False,
            ),
            content_type="application/json",
        )

    if parsed.tzinfo is None:
        parsed = parsed.replace(
            tzinfo=timezone.utc
        )

    return parsed


# =========================================
# MULTIPART FORM
# =========================================

async def read_multipart(
    request: web.Request,
) -> tuple[
    dict[str, str],
    bytes | None,
    str,
]:
    reader = await request.multipart()

    fields: dict[str, str] = {}

    image_bytes: bytes | None = None

    image_filename = "contest.jpg"

    async for part in reader:

        if part.name == "image":

            image_filename = (
                part.filename
                or "contest.jpg"
            )

            chunks = []
            total = 0

            while True:
                chunk = await part.read_chunk()

                if not chunk:
                    break

                total += len(chunk)

                if total > MAX_IMAGE_SIZE:
                    raise web.HTTPRequestEntityTooLarge(
                        max_size=MAX_IMAGE_SIZE,
                        actual_size=total,
                    )

                chunks.append(chunk)

            image_bytes = b"".join(
                chunks
            )

        else:
            fields[
                part.name
            ] = await part.text()

    return (
        fields,
        image_bytes,
        image_filename,
    )


# =========================================
# REQUIRED CHANNELS
# =========================================

def get_required_channels(
    raw: str,
) -> list[dict[str, Any]]:
    try:
        value = json.loads(raw)
    except (
        TypeError,
        json.JSONDecodeError,
    ):
        raise web.HTTPBadRequest(
            text=json.dumps(
                {
                    "error": (
                        "Majburiy kanallar "
                        "ma'lumoti noto'g'ri."
                    )
                },
                ensure_ascii=False,
            ),
            content_type="application/json",
        )

    if not isinstance(value, list):
        raise web.HTTPBadRequest(
            text=json.dumps(
                {
                    "error": (
                        "Majburiy kanallar "
                        "ma'lumoti noto'g'ri."
                    )
                },
                ensure_ascii=False,
            ),
            content_type="application/json",
        )

    return value


# =========================================
# UPLOAD IMAGE TO TELEGRAM
# =========================================

async def upload_image_to_telegram(
    bot: Bot,
    user_id: int,
    image_bytes: bytes,
    filename: str,
) -> str:
    message = await bot.send_photo(
        chat_id=user_id,
        photo=BufferedInputFile(
            image_bytes,
            filename=filename,
        ),
        caption="",
    )

    file_id = message.photo[-1].file_id

    try:
        await bot.delete_message(
            chat_id=user_id,
            message_id=message.message_id,
        )
    except Exception:
        pass

    return file_id


# =========================================
# CREATE CONTEST
# =========================================

async def api_create_contest(
    request: web.Request,
) -> web.Response:
    user = get_authenticated_user(
        request
    )

    (
        fields,
        image_bytes,
        image_filename,
    ) = await read_multipart(
        request
    )

    try:
        required_channels_input = (
            get_required_channels(
                fields.get(
                    "required_channels",
                    "[]",
                )
            )
        )

        target_value = fields.get(
            "target_channel",
            "",
        ).strip()

        post_text = fields.get(
            "post_text",
            "",
        ).strip()

        end_type = fields.get(
            "end_type",
            "",
        ).strip()

        end_at_raw = fields.get(
            "end_at",
            "",
        ).strip()

        participant_limit_raw = (
            fields.get(
                "participant_limit",
                "",
            ).strip()
        )

        winners_count = int(
            fields.get(
                "winners_count",
                "0",
            )
        )

        button_text = fields.get(
            "button_text",
            "Ishtirok etish",
        ).strip()

        start_mode = fields.get(
            "start_mode",
            "now",
        ).strip()

        start_at_raw = fields.get(
            "start_at",
            "",
        ).strip()

    except (
        TypeError,
        ValueError,
    ):
        raise web.HTTPBadRequest(
            text=json.dumps(
                {
                    "error": (
                        "Konkurs ma'lumotlarida "
                        "xato bor."
                    )
                },
                ensure_ascii=False,
            ),
            content_type="application/json",
        )

    # =====================================
    # BASIC VALIDATION
    # =====================================

    if not target_value:
        raise web.HTTPBadRequest(
            text=json.dumps(
                {
                    "error": (
                        "Konkurs kanalini "
                        "kiriting."
                    )
                },
                ensure_ascii=False,
            ),
            content_type="application/json",
        )

    if (
        not post_text
        and not image_bytes
    ):
        raise web.HTTPBadRequest(
            text=json.dumps(
                {
                    "error": (
                        "Postga matn yoki "
                        "rasm qo'shing."
                    )
                },
                ensure_ascii=False,
            ),
            content_type="application/json",
        )

    if winners_count < 1:
        raise web.HTTPBadRequest(
            text=json.dumps(
                {
                    "error": (
                        "G'oliblar soni "
                        "kamida 1 bo'lishi kerak."
                    )
                },
                ensure_ascii=False,
            ),
            content_type="application/json",
        )

    if not button_text:
        raise web.HTTPBadRequest(
            text=json.dumps(
                {
                    "error": (
                        "Ishtirok etish tugmasi "
                        "matni bo'sh bo'lmasin."
                    )
                },
                ensure_ascii=False,
            ),
            content_type="application/json",
        )

    if end_type not in {
        "time",
        "participants",
    }:
        raise web.HTTPBadRequest(
            text=json.dumps(
                {
                    "error": (
                        "Tugash sharti "
                        "noto'g'ri."
                    )
                },
                ensure_ascii=False,
            ),
            content_type="application/json",
        )

    if start_mode not in {
        "now",
        "scheduled",
    }:
        raise web.HTTPBadRequest(
            text=json.dumps(
                {
                    "error": (
                        "Boshlanish rejimi "
                        "noto'g'ri."
                    )
                },
                ensure_ascii=False,
            ),
            content_type="application/json",
        )

    # =====================================
    # TARGET CHANNEL
    # =====================================
    # FAQAT OWNER + BOT ADMIN

    target = await resolve_channel(
        bot=request.app["bot"],
        value=target_value,
        user_id=user["id"],
        require_owner=True,
        require_post_permission=True,
    )

    # =====================================
    # REQUIRED CHANNELS
    # =====================================
    # OWNER SHART EMAS
    # FAQAT BOT ADMIN BO'LISHI KERAK

    required_channels = []

    seen_ids: set[int] = set()

    # -------------------------------------
    # TARGET CHANNELNI AVTOMATIK QO'SHISH
    # -------------------------------------

    seen_ids.add(
        target["channel_id"]
    )

    required_channels.append(
        {
            "channel_id": target[
                "channel_id"
            ],
            "channel_title": target[
                "title"
            ],
            "channel_username": target[
                "username"
            ],
        }
    )

    # -------------------------------------
    # EXTRA REQUIRED CHANNELS
    # -------------------------------------

    for item in required_channels_input:

        if not isinstance(item, dict):
            continue

        value = str(
            item.get("username")
            or item.get("original")
            or item.get("value")
            or ""
        ).strip()

        if not value:
            continue

        resolved = await resolve_channel(
            bot=request.app["bot"],
            value=value,
            user_id=user["id"],
            require_owner=False,
            require_post_permission=False,
        )

        channel_id = resolved[
            "channel_id"
        ]

        if channel_id in seen_ids:
            continue

        seen_ids.add(
            channel_id
        )

        required_channels.append(
            {
                "channel_id": channel_id,
                "channel_title": (
                    resolved["title"]
                ),
                "channel_username": (
                    resolved["username"]
                ),
            }
        )

    # =====================================
    # END TIME / LIMIT
    # =====================================

    if end_type == "time":

        if not end_at_raw:
            raise web.HTTPBadRequest(
                text=json.dumps(
                    {
                        "error": (
                            "Tugash vaqtini "
                            "tanlang."
                        )
                    },
                    ensure_ascii=False,
                ),
                content_type="application/json",
            )

        end_at = parse_iso_datetime(
            end_at_raw
        )

        participant_limit = None

    else:

        try:
            participant_limit = int(
                participant_limit_raw
            )
        except ValueError:
            participant_limit = 0

        if participant_limit < 1:
            raise web.HTTPBadRequest(
                text=json.dumps(
                    {
                        "error": (
                            "Ishtirokchilar "
                            "limitini kiriting."
                        )
                    },
                    ensure_ascii=False,
                ),
                content_type="application/json",
            )

        if (
            participant_limit
            < winners_count
        ):
            raise web.HTTPBadRequest(
                text=json.dumps(
                    {
                        "error": (
                            "Ishtirokchilar soni "
                            "g'oliblardan kam "
                            "bo'lmasin."
                        )
                    },
                    ensure_ascii=False,
                ),
                content_type="application/json",
            )

        end_at = None

    # =====================================
    # START TIME
    # =====================================

    now = datetime.now(
        timezone.utc
    )

    if start_mode == "now":

        start_at = now

    else:

        if not start_at_raw:
            raise web.HTTPBadRequest(
                text=json.dumps(
                    {
                        "error": (
                            "Boshlanish vaqtini "
                            "tanlang."
                        )
                    },
                    ensure_ascii=False,
                ),
                content_type="application/json",
            )

        start_at = parse_iso_datetime(
            start_at_raw
        )

        if start_at <= now:
            raise web.HTTPBadRequest(
                text=json.dumps(
                    {
                        "error": (
                            "Boshlanish vaqti "
                            "kelajakda bo'lishi "
                            "kerak."
                        )
                    },
                    ensure_ascii=False,
                ),
                content_type="application/json",
            )

    if (
        end_at is not None
        and start_at >= end_at
    ):
        raise web.HTTPBadRequest(
            text=json.dumps(
                {
                    "error": (
                        "Boshlanish vaqti tugash "
                        "vaqtigacha bo'lishi kerak."
                    )
                },
                ensure_ascii=False,
            ),
            content_type="application/json",
        )

    # =====================================
    # OWNER DATABASE USER
    # =====================================

    owner_id = create_or_update_user(
        telegram_user_id=user["id"],
        username=user.get("username"),
        first_name=user.get("first_name"),
    )

    # =====================================
    # IMAGE
    # =====================================

    post_file_id = None

    if image_bytes:
        post_file_id = (
            await upload_image_to_telegram(
                bot=request.app["bot"],
                user_id=user["id"],
                image_bytes=image_bytes,
                filename=image_filename,
            )
        )

    # =====================================
    # DATABASE
    # =====================================

    contest_id = create_contest(
        owner_id=owner_id,
        data={
            "channel_id": target[
                "channel_id"
            ],
            "channel_title": target[
                "title"
            ],
            "channel_username": target[
                "username"
            ],
            "post_type": (
                "photo"
                if post_file_id
                else "text"
            ),
            "post_text": post_text,
            "post_file_id": post_file_id,
            "start_at": (
                start_at.isoformat()
            ),
            "end_type": (
                "participants"
                if end_type
                == "participants"
                else "time"
            ),
            "end_at": (
                end_at.isoformat()
                if end_at
                else None
            ),
            "participant_limit": (
                participant_limit
            ),
            "winners_count": (
                winners_count
            ),
            "button_text": button_text,
            "required_channels": (
                required_channels
            ),
        },
    )

    # =====================================
    # START NOW
    # =====================================

    if start_mode == "now":

        await send_contest_to_channel(
            bot=request.app["bot"],
            contest_id=contest_id,
        )

        if end_at is not None:
            schedule_contest(
                bot=request.app["bot"],
                contest_id=contest_id,
                start_at=start_at,
                end_at=end_at,
            )

    # =====================================
    # SCHEDULED
    # =====================================

    else:

        schedule_contest(
            bot=request.app["bot"],
            contest_id=contest_id,
            start_at=start_at,
            end_at=end_at,
        )

    return json_response(
        {
            "success": True,
            "contest_id": contest_id,
            "target_channel": target,
            "required_channels": (
                required_channels
            ),
        },
        status=201,
    )


# =========================================
# MY CONTESTS
# =========================================

async def api_my_contests(
    request: web.Request,
) -> web.Response:
    user = get_authenticated_user(
        request
    )

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                c.id,
                c.channel_id,
                c.channel_title,
                c.channel_username,
                c.channel_message_id,
                c.post_type,
                c.post_text,
                c.start_at,
                c.end_type,
                c.end_at,
                c.participant_limit,
                c.winners_count,
                c.button_text,
                c.status,
                c.created_at,
                (
                    SELECT COUNT(*)
                    FROM participants p
                    WHERE p.contest_id = c.id
                ) AS participants
            FROM contests c
            JOIN users u
                ON u.id = c.owner_id
            WHERE u.telegram_user_id = ?
            ORDER BY c.id DESC
            """,
            (user["id"],),
        ).fetchall()

    contests = []

    for row in rows:

        contest = dict(row)

        contest[
            "targetChannel"
        ] = {
            "channel_id": (
                contest["channel_id"]
            ),
            "title": (
                contest["channel_title"]
            ),
            "username": (
                contest["channel_username"]
            ),
        }

        contests.append(
            contest
        )

    return json_response(
        {
            "contests": contests
        }
    )


# =========================================
# HEALTH
# =========================================

async def api_health(
    request: web.Request,
) -> web.Response:
    return json_response(
        {
            "ok": True
        }
    )


# =========================================
# INDEX
# =========================================

async def index_handler(
    request: web.Request,
) -> web.StreamResponse:
    return web.FileResponse(
        WEBAPP_DIR / "index.html"
    )


# =========================================
# CREATE WEB APP
# =========================================

def create_web_app(
    bot: Bot,
) -> web.Application:

    app = web.Application(
        client_max_size=15 * 1024 * 1024
    )

    app["bot"] = bot

    app.router.add_get(
        "/",
        index_handler,
    )

    app.router.add_get(
        "/api/health",
        api_health,
    )

    app.router.add_get(
        "/api/me",
        api_me,
    )

    app.router.add_post(
        "/api/resolve-target",
        api_resolve_target,
    )

    app.router.add_post(
        "/api/contests",
        api_create_contest,
    )

    app.router.add_get(
        "/api/my-contests",
        api_my_contests,
    )

    app.router.add_static(
        "/",
        WEBAPP_DIR,
        show_index=False,
    )

    return app


# =========================================
# START SERVER
# =========================================

async def start_web_server(
    bot: Bot,
    host: str = "0.0.0.0",
    port: int = 8080,
):
    app = create_web_app(
        bot
    )

    runner = web.AppRunner(
        app
    )

    await runner.setup()

    site = web.TCPSite(
        runner,
        host,
        port,
    )

    await site.start()

    print(
        "WEBAPP SERVER ISHLAYAPTI:"
    )

    print(
        "http://127.0.0.1:8080"
    )

    return (
        runner,
        site,
    )