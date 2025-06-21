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
    (
        SELECT STRING_AGG(pn.raw_number, ', ') 
        FROM phone_numbers pn 
        WHERE pn.person_id = p.id
    ) AS all_raw_numbers,
    (
        SELECT STRING_AGG(pn.normalized_number, ', ') 
        FROM phone_numbers pn 
        WHERE pn.person_id = p.id
    ) AS all_normalized_numbers
FROM people p
WHERE p.iin = $1
LIMIT 1;
    """
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, iin)
    
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










