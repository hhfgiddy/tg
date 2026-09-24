import os

from dotenv import load_dotenv


load_dotenv()


BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")


if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN topilmadi. .env faylini tekshiring."
    )


if not ADMIN_ID:
    raise RuntimeError(
        "ADMIN_ID topilmadi. .env faylini tekshiring."
    )


try:
    ADMIN_ID = int(ADMIN_ID)
except ValueError:
    raise RuntimeError(
        "ADMIN_ID raqam bo‘lishi kerak."
    )