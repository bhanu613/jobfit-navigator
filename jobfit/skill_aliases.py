from .database import connect_database

def normalise_skill_wording(text):
    if not isinstance(text, str):
        raise ValueError('Skill wording must be text.')
    normalised = ' '.join(text.lower().split())
    if not normalised:
        raise ValueError('Skill wording must not be blank.')
    return normalised

def add_skill_alias(alias, skill_id, *, database_path=None):
    normalised_alias = normalise_skill_wording(alias)
    if type(skill_id) is not int or skill_id <= 0:
        raise ValueError('skill_id must be a positive integer.')
    connection = connect_database(database_path=database_path)
    try:
        connection.execute('\n            INSERT INTO skill_aliases (alias, skill_id)\n            VALUES (?, ?)\n            ON CONFLICT (alias) DO NOTHING\n            ', (normalised_alias, skill_id))
        existing_skill_id = connection.execute('\n            SELECT skill_id\n            FROM skill_aliases\n            WHERE alias = ?\n            ', (normalised_alias,)).fetchone()[0]
        if existing_skill_id != skill_id:
            raise ValueError(f'Alias {normalised_alias!r} already points to skill {existing_skill_id}, not skill {skill_id}.')
        connection.commit()
    finally:
        connection.close()

def resolve_skill_alias(text, *, database_path=None):
    normalised_alias = normalise_skill_wording(text)
    connection = connect_database(database_path=database_path)
    try:
        row = connection.execute('\n            SELECT skill_id\n            FROM skill_aliases\n            WHERE alias = ?\n            ', (normalised_alias,)).fetchone()
        if row is None:
            return None
        return row[0]
    finally:
        connection.close()
