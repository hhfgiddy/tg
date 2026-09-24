from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.config import ADMIN_ID
from bot.keyboards.help import help_keyboard
from bot.keyboards.main import main_menu


router = Router()


HELP_TEXT = (
    "ℹ️ <b>Yordam</b>\n\n"
    "Quyidagi bo‘limlardan keraklisini tanlang."
)


@router.message(F.text == "ℹ️ Yordam")
async def help_handler(message: Message) -> None:
    await message.answer(
        HELP_TEXT,
        reply_markup=help_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "help_back")
async def help_back_handler(
    callback: CallbackQuery,
) -> None:
    await callback.message.delete()

    await callback.message.answer(
        "🏠 <b>Asosiy menyu</b>",
        reply_markup=main_menu(
            user_id=callback.from_user.id,
        ),
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(F.data == "help_create_contest")
async def help_create_contest_handler(
    callback: CallbackQuery,
) -> None:
    await callback.message.edit_text(
        "➕ <b>Konkurs yaratish</b>\n\n"
        "1️⃣ Konkurs joylashtiriladigan kanalni tanlaysiz\n"
        "2️⃣ Konkurs postini yuborasiz\n"
        "3️⃣ Majburiy obuna kanallarini qo‘shasiz\n"
        "4️⃣ Tugash shartini belgilaysiz\n"
        "5️⃣ G‘oliblar sonini tanlaysiz\n"
        "6️⃣ Ishtirok etish tugmasini sozlaysiz\n"
        "7️⃣ Boshlanish vaqtini belgilaysiz\n\n"
        "Shundan keyin konkurs avtomatik ravishda "
        "belgilangan vaqtda boshlanadi.",
        reply_markup=help_keyboard(),
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(F.data == "help_my_contests")
async def help_my_contests_handler(
    callback: CallbackQuery,
) -> None:
    await callback.message.edit_text(
        "📋 <b>Konkurslarim</b>\n\n"
        "Bu bo‘limda siz yaratgan konkurslar "
        "ko‘rsatiladi.\n\n"
        "Siz o‘z konkurslaringizni ko‘rishingiz va "
        "ularni boshqarishingiz mumkin.",
        reply_markup=help_keyboard(),
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(F.data == "help_participation")
async def help_participation_handler(
    callback: CallbackQuery,
) -> None:
    await callback.message.edit_text(
        "🎟 <b>Konkursda qatnashish</b>\n\n"
        "Kanalda konkurs postidagi "
        "<b>Ishtirok etish</b> tugmasini bosing.\n\n"
        "Bot sizdan kerakli kanallarga obuna "
        "bo‘lishni so‘raydi.\n\n"
        "Barcha shartlarni bajarganingizdan so‘ng "
        "konkursda avtomatik qatnashasiz.",
        reply_markup=help_keyboard(),
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(F.data == "help_winners")
async def help_winners_handler(
    callback: CallbackQuery,
) -> None:
    await callback.message.edit_text(
        "🏆 <b>G‘oliblar</b>\n\n"
        "Konkurs tugagandan so‘ng bot "
        "ishtirokchilar orasidan g‘oliblarni "
        "tasodifiy ravishda tanlaydi.\n\n"
        "G‘oliblar konkurs yakunlangandan keyin "
        "ko‘rsatiladi.",
        reply_markup=help_keyboard(),
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(F.data == "help_faq")
async def help_faq_handler(
    callback: CallbackQuery,
) -> None:
    await callback.message.edit_text(
        "❓ <b>FAQ</b>\n\n"
        "<b>Botdan foydalanish pullikmi?</b>\n"
        "Hozircha botdan foydalanish bepul.\n\n"
        "<b>Konkursga qanday qatnashaman?</b>\n"
        "Konkurs postidagi ishtirok etish "
        "tugmasini bosing va ko‘rsatilgan "
        "kanallarga obuna bo‘ling.\n\n"
        "<b>G‘olib qanday tanlanadi?</b>\n"
        "G‘oliblar ishtirokchilar orasidan "
        "tasodifiy tanlanadi.\n\n"
        "<b>Konkurs qachon tugaydi?</b>\n"
        "Konkurs egasi belgilagan vaqt yoki "
        "ishtirokchilar soniga yetganda tugaydi.",
        reply_markup=help_keyboard(),
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(F.data == "help_admin")
async def help_admin_handler(
    callback: CallbackQuery,
) -> None:
    admin_link = (
        f'<a href="tg://user?id={ADMIN_ID}">'
        "👨‍💻 Admin profiliga o‘tish"
        "</a>"
    )

    await callback.message.edit_text(
        "👨‍💻 <b>Admin bilan bog‘lanish</b>\n\n"
        "Savol yoki muammo bo‘lsa admin bilan "
        "bog‘lanishingiz mumkin.\n\n"
        f"{admin_link}",
        reply_markup=help_keyboard(),
        parse_mode="HTML",
    )

    await callback.answer()