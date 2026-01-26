from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from urllib.parse import quote
import re


def create_phone_buttons(phones: list[str], name) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for number in phones:
        clean_number = re.sub(r"\D", "", number)
        if not clean_number.startswith("7"):
            continue  # Пропускаем неказахстанские




        builder.row(
            InlineKeyboardButton(text=f"💬 Telegram", url=f"https://t.me/+{clean_number}"),

            InlineKeyboardButton(text=f"📱WhatsApp", url=f"https://wa.me/+{clean_number}")
        )

    return builder.as_markup()


def invite_friends_keyboard(bot_username: str, user_id: int) -> InlineKeyboardMarkup:
    link = f"https://t.me/{bot_username}?start=ref_{user_id}"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Пригласить друзей", url=link)]
    ])





keyboardToChannel = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Перейти в канал", url="https://t.me/+7ENrGeV-zEA3NzMy")]
    ])