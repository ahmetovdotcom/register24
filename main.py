import asyncio
import re
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup


from config import BOT_TOKEN, ADMIN_ID
from db import get_pool, get_person_by_phone, get_person_by_iin
from utils import calculate_age, format_person, add_user, is_user_allowed, get_user_list, remove_user, is_authorized
from keyboards import create_phone_buttons, keyboardToChannel
from datetime import datetime, timedelta




bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
pool = None


@dp.message(CommandStart())
async def cmd_start(message: Message):
    text = (
        "👋 Добро пожаловать в бота для поиска информации на основе утечки данных по Казахстану.\n\n"
        "🔍 В базе содержится информация о <b>16 миллионах граждан</b>, собранная из недавней утечки. "
        "Вы можете найти человека по <b>ИИН</b> или <b>номеру телефона</b>.\n\n"
        "📌 <b>Форматы поддерживаются:</b>\n"
        "├ ИИН — 12 цифр (например, <code>040404540484</code>)\n"
        "├ Номер телефона — 11 цифр, начинающихся с 7 (например, <code>77771113388</code>)\n"
        "└ Не беспокойтесь о пробелах, +, -, скобках — они обрежутся автоматически.\n\n"
        "📢 Рекомендуем подписаться на наш канал, чтобы быть в курсе обновлений\n\n"
        "Введите ИИН или номер телефона для начала поиска:"
    )

    

    await message.answer(text, parse_mode="HTML", reply_markup=keyboardToChannel)

@dp.message(Command("users"))
async def list_users(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    users = get_user_list()
    if not users:
        await message.answer("📭 Список пользователей пуст.")
        return

    text = "📋 <b>Список пользователей:</b>\n\n"
    for uid, info in users.items():
        name = f"{info.get('first_name', '')} {info.get('last_name', '')}".strip()
        username = f"@{info.get('username')}" if info.get('username') else "—"
        text += f"• <b>{name}</b> {username} — <code>{uid}</code>\n/remove_{uid}\n\n"

    await message.answer(text, parse_mode="HTML")


@dp.message(F.text.startswith("/remove_"))
async def remove_user_command(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    user_id = int(message.text.split("_")[1])
    remove_user(user_id)
    await message.answer(f"❌ Пользователь {user_id} удалён.")
    try:
        await bot.send_message(user_id, "⚠️ Ваш доступ к боту был удалён администратором.")
    except:
        pass  # если пользователь заблокировал бота



@dp.callback_query(F.data == "request_access")
async def request_access(callback: CallbackQuery):
    await callback.message.edit_text("✅ Запрос отправлен администратору. Пожалуйста, ожидайте одобрения.")
    user = callback.from_user
    await callback.answer("⏳ Запрос отправлен админу.")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ 7 дней", callback_data=f"grant:{user.id}:7")],
        [InlineKeyboardButton(text="✅ 14 дней", callback_data=f"grant:{user.id}:14")],
        [InlineKeyboardButton(text="✅ 30 дней", callback_data=f"grant:{user.id}:30")],
        [InlineKeyboardButton(text="✅ Навсегда", callback_data=f"grant:{user.id}:0")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"deny:{user.id}")]
    ])

    await bot.send_message(ADMIN_ID,
        f"📥 Запрос от @{user.username or '-'}\nID: {user.id}\nИмя: {user.first_name}",
        reply_markup=keyboard)
    
    
@dp.callback_query(F.data.startswith("grant:"))
async def grant_access(callback: CallbackQuery):
    _, user_id, days = callback.data.split(":")
    user_id = int(user_id)
    days = int(days)

    user = await bot.get_chat(user_id)

    # Вычисляем дату окончания
    if days == 0:
        until = "бессрочно"
    else:
        end_date = datetime.now() + timedelta(days=days)
        until = end_date.strftime("%d.%m.%Y")

    # Добавляем пользователя с датой окончания
    add_user(user_id, user.first_name, user.last_name or "", user.username or "", days)

    await callback.answer("✅ Доступ выдан.")

    # Сообщение для пользователя
    try:
        await bot.send_message(
            user_id,
            f"✅ Вам выдан доступ до {until}." if days else "✅ Вам выдан постоянный доступ."
        )
    except:
        pass

    # Обновляем сообщение админа (удаляем кнопки + пишем кому выдано)
    full_name = f"{user.first_name} {user.last_name}".strip()
    username = f"@{user.username}" if user.username else ""
    await callback.message.edit_text(
        f"✅ Доступ выдан пользователю {full_name} {username} (ID: <code>{user_id}</code>) до <b>{until}</b>.",
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("deny:"))
async def deny_access(callback: CallbackQuery):
    _, user_id = callback.data.split(":")
    await callback.answer("❌ Запрос отклонён.")
    try:
        await bot.send_message(user_id, "🚫 Ваш запрос на доступ был отклонён.")
    except:
        pass










@dp.message(F.text)
@is_authorized
async def handle_input(message: Message, **kwargs):
    global pool
    text = message.text.strip()
    digits = re.sub(r"\D", "", text)

    loading_msg = await message.answer("🔍 Идёт поиск...")
    person = None  # ← Добавили безопасную инициализацию

    try:
        if len(digits) == 12:
            person = await get_person_by_iin(pool, digits)
            if person:
                result = "✅ Найден по ИИН:\n\n" + format_person(person)
            else:
                result = "❌ Пользователь с таким ИИН не найден."

        elif len(digits) == 11 and digits.startswith("7"):
            person = await get_person_by_phone(pool, digits)
            if person:
                result = "✅ Найден по номеру:\n\n" + format_person(person)
            else:
                result = "❌ Пользователь с таким номером не найден."
        else:
            result = "❗ Пожалуйста, отправьте корректный ИИН (12 цифр) или номер телефона (11 цифр, начиная с 7)."

    except Exception as e:
        result = f"⚠️ Ошибка при поиске: {e}"

    await loading_msg.delete()

    if person:
        phones_raw = person['all_raw_numbers'] or ''
        phones_list = phones_raw.split(', ')
        keyboard = create_phone_buttons(phones_list)
        await message.answer(result, parse_mode="HTML", reply_markup=keyboard)
    else:
        await message.answer(result)

async def main():
    global pool
    pool = await get_pool()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())