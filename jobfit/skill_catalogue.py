from .database import connect_database
from .job_store import initialise_database, get_or_create_skill
from .skill_aliases import add_skill_alias
STARTER_SKILLS = (('python', 'Python'), ('sql', 'SQL'), ('docker', 'Docker'), ('scikit-learn', 'Scikit-learn'))
STARTER_ALIASES = (('python', 'python'), ('sql', 'sql'), ('structured query language', 'sql'), ('docker', 'docker'), ('scikit-learn', 'scikit-learn'), ('sklearn', 'scikit-learn'), ('scikit learn', 'scikit-learn'))

def seed_skill_catalogue(*, database_path=None):
    skill_ids = {}
    for skill_key, canonical_name in STARTER_SKILLS:
        skill_ids[skill_key] = get_or_create_skill(skill_key, canonical_name, database_path=database_path)
    return skill_ids

def seed_skill_aliases(*, database_path=None):
    connection = connect_database(database_path=database_path)
    try:
        rows = connection.execute('SELECT skill_key, skill_id FROM skills').fetchall()
        skill_ids = dict(rows)
    finally:
        connection.close()
    missing_keys = {skill_key for _, skill_key in STARTER_ALIASES if skill_key not in skill_ids}
    if missing_keys:
        raise ValueError(f'Create the catalogue before seeding aliases. Missing keys: {sorted(missing_keys)}')
    for alias, skill_key in STARTER_ALIASES:
        add_skill_alias(alias, skill_ids[skill_key], database_path=database_path)
if __name__ == '__main__':
    initialise_database()
    seed_skill_catalogue()
    seed_skill_aliases()
    print('Starter skill catalogue and aliases are ready.')
