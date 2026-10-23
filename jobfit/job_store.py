import sys
from urllib.parse import urlsplit
from .database import connect_database

def validate_source_url(source_url):
    if source_url is None:
        return
    if not isinstance(source_url, str):
        raise TypeError('Source URL must be text or None.')
    if any((character.isspace() for character in source_url)):
        raise ValueError('Source URL cannot contain whitespace.')
    try:
        parsed_url = urlsplit(source_url)
    except ValueError as error:
        raise ValueError('Source URL could not be parsed.') from error
    if parsed_url.scheme not in ('http', 'https') or not parsed_url.hostname:
        raise ValueError('Source URL must include http:// or https:// and a hostname.')

def validate_job_input(title, description_text, source_description, source_url=None):
    if not isinstance(title, str):
        raise TypeError('Job title must be text.')
    if not title.strip():
        raise ValueError('Job title cannot be blank.')
    if not isinstance(description_text, str):
        raise TypeError('Job description must be text.')
    if not description_text.strip():
        raise ValueError('Job description cannot be blank.')
    if not isinstance(source_description, str):
        raise TypeError('Source description must be text.')
    if not source_description.strip():
        raise ValueError('Source description cannot be blank.')
    validate_source_url(source_url)

def validate_candidate_skill_input(candidate_id, skill_id, evidence_status, evidence_note):
    for field_name, value in (('candidate_id', candidate_id), ('skill_id', skill_id)):
        if type(value) is not int or value <= 0:
            raise ValueError(f'{field_name} must be a positive integer.')
    allowed_statuses = ('evidenced', 'developing', 'self_reported')
    if evidence_status not in allowed_statuses:
        raise ValueError("evidence_status must be 'evidenced', 'developing', or 'self_reported'.")
    if evidence_note is not None and (not isinstance(evidence_note, str)):
        raise ValueError('evidence_note must be text or None.')
    if evidence_status == 'evidenced':
        if evidence_note is None or not evidence_note.strip():
            raise ValueError('An evidenced skill must have a nonblank evidence_note.')

def save_job(title, description_text, source_description, source_url=None, *, database_path=None):
    validate_job_input(title, description_text, source_description, source_url)
    connection = connect_database(database_path=database_path)
    try:
        cursor = connection.execute('\n            INSERT INTO jobs (\n                title, description_text, source_description, source_url\n            )\n            VALUES (?, ?, ?, ?)\n            ', (title, description_text, source_description, source_url))
        new_job_id = cursor.lastrowid
        connection.commit()
        return new_job_id
    finally:
        connection.close()

def save_candidate_skill(candidate_id, skill_id, evidence_status, evidence_note=None, *, database_path=None):
    validate_candidate_skill_input(candidate_id, skill_id, evidence_status, evidence_note)
    connection = connect_database(database_path=database_path)
    try:
        connection.execute('\n            INSERT INTO candidate_skills (\n                candidate_id,\n                skill_id,\n                evidence_status,\n                evidence_note\n            )\n            VALUES (?, ?, ?, ?)\n            ON CONFLICT (candidate_id, skill_id)\n            DO UPDATE SET\n                evidence_status = excluded.evidence_status,\n                evidence_note = excluded.evidence_note\n            ', (candidate_id, skill_id, evidence_status, evidence_note))
        connection.commit()
    finally:
        connection.close()

def create_candidate(display_name=None, *, database_path=None):
    if display_name is not None:
        if not isinstance(display_name, str) or not display_name.strip():
            raise ValueError('display_name must be nonblank text or None.')
        display_name = display_name.strip()
    connection = connect_database(database_path=database_path)
    try:
        cursor = connection.execute('\n            INSERT INTO candidates (display_name)\n            VALUES (?)\n            ', (display_name,))
        candidate_id = cursor.lastrowid
        connection.commit()
        return candidate_id
    finally:
        connection.close()

def get_or_create_skill(skill_key, canonical_name, *, database_path=None):
    for field_name, value in (('skill_key', skill_key), ('canonical_name', canonical_name)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f'{field_name} must be nonblank text.')
    skill_key = skill_key.strip()
    canonical_name = canonical_name.strip()
    connection = connect_database(database_path=database_path)
    try:
        connection.execute('\n            INSERT INTO skills (skill_key, canonical_name)\n            VALUES (?, ?)\n            ON CONFLICT (skill_key) DO NOTHING\n            ', (skill_key, canonical_name))
        row = connection.execute('\n            SELECT skill_id, canonical_name\n            FROM skills\n            WHERE skill_key = ?\n            ', (skill_key,)).fetchone()
        skill_id, existing_name = row
        if existing_name != canonical_name:
            raise ValueError(f'Skill key {skill_key!r} already belongs to {existing_name!r}, not {canonical_name!r}.')
        connection.commit()
        return skill_id
    finally:
        connection.close()

def read_candidate_skills(candidate_id, *, database_path=None):
    if type(candidate_id) is not int or candidate_id <= 0:
        raise ValueError('candidate_id must be a positive integer.')
    connection = connect_database(database_path=database_path)
    try:
        candidate = connection.execute('\n            SELECT candidate_id\n            FROM candidates\n            WHERE candidate_id = ?\n            ', (candidate_id,)).fetchone()
        if candidate is None:
            raise ValueError(f'Candidate {candidate_id} does not exist.')
        rows = connection.execute('\n            SELECT\n                cs.candidate_id,\n                s.skill_id,\n                s.skill_key,\n                s.canonical_name,\n                cs.evidence_status,\n                cs.evidence_note\n            FROM candidate_skills AS cs\n            JOIN skills AS s\n                ON s.skill_id = cs.skill_id\n            WHERE cs.candidate_id = ?\n            ORDER BY s.skill_key\n            ', (candidate_id,)).fetchall()
        return [{'candidate_id': row[0], 'skill_id': row[1], 'skill_key': row[2], 'canonical_name': row[3], 'evidence_status': row[4], 'evidence_note': row[5]} for row in rows]
    finally:
        connection.close()

def initialise_database(*, database_path=None):
    connection = connect_database(database_path=database_path)
    try:
        connection.execute("\n            CREATE TABLE IF NOT EXISTS jobs (\n                job_id INTEGER PRIMARY KEY,\n                title TEXT NOT NULL,\n                description_text TEXT NOT NULL,\n                source_description TEXT NOT NULL,\n                source_url TEXT,\n                date_added TEXT NOT NULL DEFAULT CURRENT_DATE,\n                application_status TEXT NOT NULL DEFAULT 'Not applied'\n            )\n        ")
        connection.execute('\n            CREATE TABLE IF NOT EXISTS candidates (\n                candidate_id INTEGER PRIMARY KEY,\n                display_name TEXT\n            )\n        ')
        connection.execute('\n            CREATE TABLE IF NOT EXISTS skills (\n                skill_id INTEGER PRIMARY KEY,\n                skill_key TEXT NOT NULL UNIQUE,\n                canonical_name TEXT NOT NULL,\n                esco_uri TEXT UNIQUE\n            )\n        ')
        connection.execute("\n            CREATE TABLE IF NOT EXISTS candidate_skills (\n                candidate_id INTEGER NOT NULL,\n                skill_id INTEGER NOT NULL,\n\n                evidence_status TEXT NOT NULL\n                    CHECK (\n                        evidence_status IN (\n                            'evidenced',\n                            'developing',\n                            'self_reported'\n                        )\n                    ),\n\n                evidence_note TEXT,\n\n                PRIMARY KEY (candidate_id, skill_id),\n\n                FOREIGN KEY (candidate_id)\n                    REFERENCES candidates(candidate_id),\n\n                FOREIGN KEY (skill_id)\n                    REFERENCES skills(skill_id),\n\n                CHECK (\n                    evidence_status != 'evidenced'\n                    OR (\n                        evidence_note IS NOT NULL\n                        AND length(\n                            trim(\n                                evidence_note,\n                                char(9) || char(10) || char(13) || ' '\n                            )\n                        ) > 0\n                    )\n                )\n            )\n        ")
        connection.execute('\n            CREATE TABLE IF NOT EXISTS skill_aliases (\n                alias TEXT PRIMARY KEY NOT NULL,\n                skill_id INTEGER NOT NULL,\n\n                CHECK (length(trim(alias)) > 0),\n\n                FOREIGN KEY (skill_id)\n                    REFERENCES skills(skill_id)\n            )\n        ')
        connection.commit()
    finally:
        connection.close()
if __name__ == '__main__':
    initialise_database()
    print('Jobs, candidates, skills, and candidate-skills tables are ready.')
    if '--add-example' in sys.argv:
        title = 'Working Student - Data Quality'
        description_text = 'This fictional role uses SQL to check data completeness.'
        source_description = 'Fictional company vacancy used for function testing'
        source_url = None
        new_job_id = save_job(title, description_text, source_description, source_url)
        print('Saved job ID:', new_job_id)
    else:
        print('No job added. Use --add-example only when you want another test row.')
