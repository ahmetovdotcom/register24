import asyncpg
from config import host, user, password, db_name


async def get_pool():
    return await asyncpg.create_pool(
        user=user,
        password=password,
        database=db_name,
        host=host
    )


async def get_person_by_iin(pool, iin: str):
    async with pool.acquire() as conn:
        # 1. Быстрый поиск по IIN без JOIN
        person = await conn.fetchrow("""
            SELECT 
                id, surname, name, patronymic, gender, birth_date,
                identifier, iin, citizenship, nationality,
                address, address_confirmed, residence_start, residence_end
            FROM people
            WHERE iin = $1
            LIMIT 1
        """, iin)

        if not person:
            return None

        # 2. Поиск телефонов по person_id
        phones = await conn.fetch("""
            SELECT raw_number, normalized_number
            FROM phone_numbers
            WHERE person_id = $1
        """, person['id'])

        # 3. Агрегация телефонов (как раньше)
        all_raw = ', '.join([r['raw_number'] for r in phones])
        all_norm = ', '.join([r['normalized_number'] for r in phones])

        # 4. Объединение в единый результат
        result = dict(person)
        result['all_raw_numbers'] = all_raw
        result['all_normalized_numbers'] = all_norm

        return result
    
async def get_person_by_phone(pool, phone: str):
    query = """
    SELECT 
        p.id,
        p.surname,
        p.name,
        p.patronymic,
        p.gender,
        p.birth_date,
        p.identifier,
        p.iin,
        p.citizenship,
        p.nationality,
        p.address,
        p.address_confirmed,
        p.residence_start,
        p.residence_end,
        STRING_AGG(pn.raw_number, ', ') AS all_raw_numbers,
        STRING_AGG(pn.normalized_number, ', ') AS all_normalized_numbers
    FROM people p
    JOIN phone_numbers pn ON pn.person_id = p.id
    WHERE pn.normalized_number = $1
    GROUP BY p.id, p.surname, p.name, p.iin
    LIMIT 1
    """
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, phone)










