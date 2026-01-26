import os
import json
from datetime import datetime, timedelta
from datetime import date
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

USERS_FILE = "allowed_users.json"
REF_REQUIRED = 2

def is_authorized(func):
    async def wrapper(message: Message, *args, **kwargs):
        if is_user_allowed(message.from_user.id):
            return await func(message, *args, **kwargs)
        else:
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
    return wrapper


def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)



def add_user(user_id, first_name="", last_name="", username="", days=0):
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump({}, f)

    with open(USERS_FILE, "r") as f:
        users = json.load(f)

    access_until = None
    if days > 0:
        access_until = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

    users[str(user_id)] = {
        "first_name": first_name,
        "last_name": last_name,
        "username": username,
        "access_until": access_until
    }

    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def remove_user(user_id):
    users = get_user_list()
    users.pop(str(user_id), None)
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


def get_user_list():
    if not os.path.exists(USERS_FILE):
        return {}

    with open(USERS_FILE, "r") as f:
        return json.load(f)

def is_user_allowed(user_id):
    users = get_user_list()
    user = users.get(str(user_id))
    if not user:
        return False

    access_until = user.get("access_until")
    if access_until:
        try:
            return datetime.now().date() <= datetime.strptime(access_until, "%Y-%m-%d").date()
        except:
            return False
    return True






def calculate_age(birth_date):
    today = date.today()
    if not birth_date:
        return "—"
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

def format_person(p, user_id: int):
    age = calculate_age(p['birth_date'])

    full_access = has_ref_access(user_id)

    phones = p['all_raw_numbers'] or '—'
    phones_list = phones.split(', ')
    phones_block = "\n".join([f"├ Номер: {num}" for num in phones_list])

    address = p['address'] if full_access else "🔒 Доступ ограничен"
    iin = f"<code>{p['iin']}</code>" if full_access else "🔒 Доступ ограничен\n\nПригласите 2 друзей и получите доступ ко всем функциям!"

    return (
        f"📱 Телефон\n"
        f"{phones_block}\n"
        f"└ Гражданство: {p['citizenship']}\n\n"

        f"👤 Основные данные\n"
        f"├ ФИО: {p['surname']} {p['name']} {p['patronymic']}\n"
        f"├ Дата рождения: {p['birth_date'].strftime('%d.%m.%Y') if p['birth_date'] else '—'}\n"
        f"└ Возраст: {age}\n"
        f"└ Нация: {p['nationality']}\n"
        f"└ Пол: {p['gender']}\n\n"

        f"🏠 Адрес\n"
        f"{address}\n\n"

        f"🆔 ИИН: {iin}\n"
    )



def has_ref_access(user_id: int) -> bool:
    users = get_user_list()
    user = users.get(str(user_id))
    if not user:
        return False
    return user.get("invited", 0) >= REF_REQUIRED


def register_referral(new_user_id: int, referrer_id: int):
    users = get_user_list()

    # если приглашаемый уже есть — НЕ считаем
    if str(new_user_id) in users:
        return

    # если сам себя — тоже нет
    if new_user_id == referrer_id:
        return

    # создаём запись для нового пользователя
    users[str(new_user_id)] = {
        "first_name": "",
        "last_name": "",
        "username": "",
        "access_until": None,
        "invited": 0,
        "referrer": referrer_id
    }

    # увеличиваем счётчик пригласившему
    if str(referrer_id) in users:
        users[str(referrer_id)]["invited"] = (
            users[str(referrer_id)].get("invited", 0) + 1
        )

    save_users(users)
