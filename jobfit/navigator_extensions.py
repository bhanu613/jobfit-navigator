"""Additive local review, language, library and export services."""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
STATUSES = ('required', 'desirable', 'not_required', 'uncertain')
APPLICATION_STATUSES = ('Not applied', 'Considering', 'Applied', 'Interview', 'Offer', 'Closed')
LANGUAGES = ('German', 'English', 'French', 'Spanish', 'Other')
LEVELS = ('Not specified', 'A1', 'A2', 'B1', 'B2', 'C1', 'C2', 'Native / bilingual (self-described)')

def connect(path):
    connection = sqlite3.connect(path)
    connection.execute('PRAGMA foreign_keys = ON')
    connection.row_factory = sqlite3.Row
    return connection

def fetch(path, sql, parameters=()):
    connection = connect(path)
    try:
        return [dict(row) for row in connection.execute(sql, parameters)]
    finally:
        connection.close()

def initialise_extensions(path):
    connection = connect(path)
    try:
        with connection:
            connection.execute("CREATE TABLE IF NOT EXISTS navigator_reviews_v2 (\n                job_id INTEGER NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,\n                source_hash TEXT NOT NULL,\n                skill_id INTEGER NOT NULL REFERENCES skills(skill_id),\n                start_offset INTEGER NOT NULL,\n                end_offset INTEGER NOT NULL,\n                reviewed_status TEXT NOT NULL CHECK(reviewed_status IN ('required','desirable','not_required','uncertain')),\n                review_note TEXT NOT NULL,\n                rule_status_at_review TEXT NOT NULL,\n                rule_id_at_review TEXT NOT NULL,\n                reviewed_at TEXT NOT NULL,\n                PRIMARY KEY(job_id, source_hash, skill_id, start_offset, end_offset)\n            )")
            connection.execute('CREATE TABLE IF NOT EXISTS navigator_languages_v2 (\n                candidate_id INTEGER NOT NULL REFERENCES candidates(candidate_id) ON DELETE CASCADE,\n                language TEXT NOT NULL,\n                reported_level TEXT NOT NULL,\n                note TEXT NOT NULL,\n                PRIMARY KEY(candidate_id, language)\n            )')
    finally:
        connection.close()

def source_hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def require_job(connection, job_id):
    row = connection.execute('SELECT * FROM jobs WHERE job_id = ?', (job_id,)).fetchone()
    if row is None:
        raise ValueError('Job does not exist.')
    return dict(row)

def save_review(path, job_id, source_text, mention, reviewed_status, note):
    if reviewed_status not in STATUSES:
        raise ValueError('Invalid review status.')
    if not isinstance(note, str) or not note.strip():
        raise ValueError('Add a short reason or confirmation note.')
    start, end = (mention['start'], mention['end'])
    if type(start) is not int or type(end) is not int or (not 0 <= start < end <= len(source_text)):
        raise ValueError('Invalid source offsets.')
    if source_text[start:end] != mention['matched_text']:
        raise ValueError('The mention does not match the original source.')
    connection = connect(path)
    try:
        with connection:
            job = require_job(connection, job_id)
            if job['description_text'] != source_text:
                raise ValueError('The source changed. Reload the analysis before reviewing.')
            connection.execute('INSERT INTO navigator_reviews_v2 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)\n                ON CONFLICT(job_id, source_hash, skill_id, start_offset, end_offset)\n                DO UPDATE SET reviewed_status=excluded.reviewed_status,\n                    review_note=excluded.review_note,\n                    rule_status_at_review=excluded.rule_status_at_review,\n                    rule_id_at_review=excluded.rule_id_at_review,\n                    reviewed_at=excluded.reviewed_at', (job_id, source_hash(source_text), mention['skill_id'], start, end, reviewed_status, note.strip(), mention['requirement_status'], mention['rule_id'], datetime.now(timezone.utc).isoformat()))
    finally:
        connection.close()

def attach_reviews(path, job_id, text, mentions):
    rows = fetch(path, 'SELECT * FROM navigator_reviews_v2 WHERE job_id=? AND source_hash=?', (job_id, source_hash(text)))
    reviews = {(row['skill_id'], row['start_offset'], row['end_offset']): row for row in rows}
    return [{**mention, 'review': reviews.get((mention['skill_id'], mention['start'], mention['end']))} for mention in mentions]

def remove_review(path, job_id, text, mention):
    connection = connect(path)
    try:
        with connection:
            connection.execute('DELETE FROM navigator_reviews_v2 WHERE job_id=? AND source_hash=? AND skill_id=? AND start_offset=? AND end_offset=?', (job_id, source_hash(text), mention['skill_id'], mention['start'], mention['end']))
    finally:
        connection.close()

def save_language(path, candidate_id, language, level, note=''):
    if language not in LANGUAGES or level not in LEVELS or (not isinstance(note, str)):
        raise ValueError('Choose a listed language and level; note must be text.')
    connection = connect(path)
    try:
        with connection:
            connection.execute('INSERT INTO navigator_languages_v2 VALUES (?, ?, ?, ?)\n                ON CONFLICT(candidate_id, language) DO UPDATE SET reported_level=excluded.reported_level, note=excluded.note', (candidate_id, language, level, note.strip()))
    finally:
        connection.close()

def list_languages(path, candidate_id):
    return fetch(path, 'SELECT language, reported_level, note FROM navigator_languages_v2 WHERE candidate_id=? ORDER BY language', (candidate_id,))

def remove_language(path, candidate_id, language):
    connection = connect(path)
    try:
        with connection:
            connection.execute('DELETE FROM navigator_languages_v2 WHERE candidate_id=? AND language=?', (candidate_id, language))
    finally:
        connection.close()

def update_application_status(path, job_id, status):
    if status not in APPLICATION_STATUSES:
        raise ValueError('Invalid application status.')
    connection = connect(path)
    try:
        with connection:
            require_job(connection, job_id)
            connection.execute('UPDATE jobs SET application_status=? WHERE job_id=?', (status, job_id))
    finally:
        connection.close()

def delete_job(path, job_id):
    connection = connect(path)
    try:
        with connection:
            require_job(connection, job_id)
            connection.execute('DELETE FROM jobs WHERE job_id=?', (job_id,))
    finally:
        connection.close()

def make_report(job, candidate_id, mentions, languages):
    return json.dumps({'format_version': 'jobfit-review-0.2', 'generated_at_utc': datetime.now(timezone.utc).isoformat(), 'candidate_id': candidate_id, 'source_sha256': source_hash(job['description_text']), 'job': job, 'mentions': mentions, 'profile_languages_self_reported': languages, 'limitations': ['Local single-user tool; not a hiring or capability assessment.', 'Human review is separate from rule output and is not automatically gold-standard annotation.', 'Language records are displayed only; language requirement extraction/comparison is not implemented.', 'Current-profile comparison, not an immutable historical profile snapshot.', 'Only approved catalogue mentions are detected; rules can be wrong.']}, ensure_ascii=False, indent=2)
