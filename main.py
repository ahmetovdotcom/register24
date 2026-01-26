import asyncio
import re
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup


from config import BOT_TOKEN, ADMIN_ID
from db import get_pool, get_person_by_phone, get_person_by_iin
from utils import has_ref_access, calculate_age, format_person, add_user, is_user_allowed, get_user_list, remove_user, is_authorized,register_referral
from keyboards import create_phone_buttons, keyboardToChannel, invite_friends_keyboard
from datetime import datetime, timedelta





bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
pool = None


@dp.message(CommandStart())

async def cmd_start(message: Message):
    user_id = message.from_user.id
    args = message.text.split()

    # 👥 РЕФЕРАЛЬНЫЙ СТАРТ
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1].replace("ref_", ""))
            register_referral(user_id, referrer_id)
        except:
            pass

    # ❌ Если пользователь не авторизован
    if not is_user_allowed(user_id):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔓 Запросить доступ", callback_data="request_access")]
        ])

        await message.answer(
            "🚫 <b>Доступ ограничен</b>\n\n"
            "Для использования бота необходимо получить разрешение администратора.\n"
            "Нажмите кнопку ниже, чтобы отправить запрос 👇",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        return

    # ✅ Если авторизован
    text = (
        "👋 Добро пожаловать в бота для поиска информации на основе утечки данных по Казахстану.\n\n"
        "🔍 В базе содержится информация о <b>16 миллионах граждан</b>, собранная из недавней утечки. "
        "Вы можете найти человека по <b>ИИН</b> или <b>номеру телефона</b>.\n\n"
        "📌 <b>Форматы поддерживаются:</b>\n"
        "├ ИИН — 12 цифр (например, <code>040404540484</code>)\n"
        "├ Номер телефона — 11 цифр, начинающихся с 7 (например, <code>77771113388</code>)\n"
        "└ Не беспокойтесь о пробелах, +, -, скобках — они обрежутся автоматически.\n\n"
        "Введите ИИН или номер телефона для поиска 👇"
    )
    await message.answer(text, parse_mode="HTML")

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

@dp.message(Command("stats"))
async def admin_stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    users = get_user_list()

    total_users = len(users)
    referred_users = sum(1 for u in users.values() if "referrer" in u)
    active_referrers = sum(1 for u in users.values() if u.get("invited", 0) > 0)

    text = (
        "📊 <b>Статистика бота</b>\n\n"
        f"👥 Всего пользователей: <b>{total_users}</b>\n"
        f"🔗 Пришли по рефералке: <b>{referred_users}</b>\n"
        f"🚀 Приглашали других: <b>{active_referrers}</b>"
    )

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
            f"✅ Вам выдан доступ до {until}." if days else "✅ Вам выдан постоянный доступ. Нажмите /start"
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


@dp.message(Command("broadcast"))
async def broadcast(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    text = message.text.replace("/broadcast", "").strip()
    if not text:
        await message.answer("❗ Использование: /broadcast текст рассылки")
        return

    users = get_user_list()

    sent = 0
    failed = 0

    await message.answer("📣 Начинаю рассылку...")

    for user_id in users.keys():
        try:
            await bot.send_message(int(user_id), text, parse_mode="HTML")
            sent += 1
            await asyncio.sleep(0.05)  # ⛔ антифлуд
        except:
            failed += 1

    await message.answer(
        f"✅ Рассылка завершена\n\n"
        f"📨 Отправлено: <b>{sent}</b>\n"
        f"❌ Ошибок: <b>{failed}</b>",
        parse_mode="HTML"
    )


@dp.message(Command("admin"))
async def broadcast(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    text = (
        "/users - юзеры\n"
        f"/stats - статистика\n"
        f"/broadcast - рассылка\n"
    )

    await message.answer(text, parse_mode="HTML")




@dp.callback_query(F.data.startswith("send_ref_"))
async def send_ref_link(callback: CallbackQuery):
    user_id = callback.data.split("_")[-1]  # получаем user_id из callback_data
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"

    await callback.message.answer(f"Вот твоя реферальная ссылка! Отправь друзьям эту ссылку: \n{link}")
    await callback.answer()  # закрывает "часики" у кнопки


    










@dp.message(F.text)
@is_authorized
async def handle_input(message: Message, **kwargs):
    global pool

    text = message.text.strip()
    digits = re.sub(r"\D", "", text)

    loading_msg = await message.answer("🔍 Идёт поиск...")
    person = None

    try:
        # 🔎 Поиск по ИИН
        if len(digits) == 12:
            person = await get_person_by_iin(pool, digits)
            if person:
                result = "✅ Найден по ИИН:\n\n" + format_person(
                    person,
                    message.from_user.id
                )
            else:
                result = "❌ Пользователь с таким ИИН не найден."

        # 🔎 Поиск по номеру
        elif len(digits) == 11 and digits.startswith("7"):
            person = await get_person_by_phone(pool, digits)
            if person:
                result = "✅ Найден по номеру:\n\n" + format_person(
                    person,
                    message.from_user.id
                )
            else:
                result = "❌ Пользователь с таким номером не найден."

        else:
            result = (
                "❗ Пожалуйста, отправьте корректный ИИН (12 цифр) "
                "или номер телефона (11 цифр, начиная с 7)."
            )

    except Exception as e:
        result = f"⚠️ Ошибка при поиске: {e}"

    await loading_msg.delete()

    # 📤 Отправка результата
    if person:
        phones_raw = person['all_raw_numbers'] or ''
        phones_list = phones_raw.split(', ')
        name = person['name']
        phone_kb = create_phone_buttons(phones_list, name)

        # 👥 ЕСЛИ НЕТ РЕФЕРАЛОВ — ПОКАЗЫВАЕМ КНОПКУ ПРИГЛАШЕНИЯ
        if not has_ref_access(message.from_user.id):
            bot_info = await bot.me()
            invite_kb = invite_friends_keyboard(message.from_user.id)

            await message.answer(
                result,
                parse_mode="HTML",
                reply_markup=invite_kb
            )
        else:
            await message.answer(
                result,
                parse_mode="HTML",
                reply_markup=phone_kb
            )
    else:
        await message.answer(result)

async def main():
    global pool
    pool = await get_pool()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
