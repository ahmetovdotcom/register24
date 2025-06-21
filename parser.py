import csv
import re
import psycopg2
from config import host, user, password, db_name
from datetime import datetime


def normalize_phone(phone: str) -> str:
    digits = re.sub(r'\D', '', phone)
    if digits.startswith('8'):
        digits = '7' + digits[1:]
    return digits


def normalize_phone_list(phone_str):
    if not phone_str:
        return []
    numbers = phone_str.split(',')
    result = []
    for raw in numbers:
        raw = raw.strip()
        normalized = normalize_phone(raw)
        if normalized:
            result.append((raw, normalized))
    return result


def parse_date(s):
    try:
        return datetime.fromisoformat(s.strip())
    except:
        return None


try:
    connection = psycopg2.connect(
        host=host,
        user=user,
        password=password,
        dbname=db_name
    )
    connection.autocommit = True

    with connection.cursor() as cursor:
        with open('data.csv', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')
            for row in reader:
                # проверки
                iin = row['ИНН'].strip()
                if not iin:
                    print(f"[!] Пропущено: нет ИИН у {row['Фамилия'].strip()} {row['Имя'].strip()}")
                    continue

                cursor.execute("SELECT id FROM people WHERE iin = %s", (iin,))
                existing = cursor.fetchone()

                if existing:
                    print(f"[!] Пропущено: ИИН уже есть — {iin}")
                    continue

                # Вставка в таблицу people
                cursor.execute("""
                    INSERT INTO people (
                        surname, name, patronymic, gender, birth_date,
                        identifier, iin, citizenship, nationality,
                        address, address_confirmed, residence_start, residence_end
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, (
                    row['Фамилия'].strip(),
                    row['Имя'].strip(),
                    row['Отчество'].strip(),
                    row['Пол'].strip(),
                    row['Дата рождения'].strip(),
                    row['Идентификатор'].strip(),
                    row['ИНН'].strip(),
                    row['Гражданство'].strip(),
                    row['Национальность'].strip(),
                    row['Адрес'].strip(),
                    row['Адрес подтвержден'].strip().upper() == 'TRUE',
                    parse_date(row['Дата начала проживания']),
                    parse_date(row['Дата конца проживания'])
                ))

                person_id = cursor.fetchone()[0]

                all_phones_added = 0

                for type_, field in [('mobile', 'Мобильный'), ('work', 'Рабочий'), ('home', 'Домашний')]:
                    phones = normalize_phone_list(row[field])
                    for raw, normalized in phones:
                        cursor.execute("""
                            INSERT INTO phone_numbers (person_id, type, raw_number, normalized_number)
                            VALUES (%s, %s, %s, %s)
                        """, (person_id, type_, raw, normalized))
                        all_phones_added += 1

                # Печать инфы о человеке
                print(f"[+] Добавлен: {row['Фамилия'].strip()} {row['Имя'].strip()} {row['Отчество'].strip()} | ИИН: {row['ИНН'].strip()} | Номеров: {all_phones_added}")
                print("-" * 80)
                

    print("[INFO] Import completed successfully!")

except Exception as _ex:
    print("[ERROR] Error while working with PostgreSQL:", _ex)

finally:
    if connection:
        connection.close()
        print("[INFO] PostgreSQL connection closed")