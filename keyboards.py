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


def invite_friends_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """
    Кнопка с callback_data, чтобы бот прислал ссылку
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Пригласить друзей", callback_data=f"send_ref_{user_id}")]
    ])




keyboardToChannel = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Перейти в канал", url="https://t.me/+7ENrGeV-zEA3NzMy")]
    ])