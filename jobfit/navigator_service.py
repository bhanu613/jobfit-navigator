from .navigator_interpretation import interpret_mention
'Integration services; compatible with existing app.py and app_v2.py.'
from .database import connect_database
from .job_store import initialise_database, get_or_create_skill, read_candidate_skills
from .skill_catalogue import seed_skill_catalogue, seed_skill_aliases
from .skill_aliases import add_skill_alias
from .skill_mentions import find_skill_mentions
from .navigator_interpretation import interpret_clause, clause_bounds, has_multiple_concepts
EXTRA_SKILLS = (('pandas', 'pandas', ('pandas',)), ('numpy', 'NumPy', ('numpy',)), ('pytorch', 'PyTorch', ('pytorch',)), ('tensorflow', 'TensorFlow', ('tensorflow',)), ('git', 'Git', ('git',)), ('linux', 'Linux', ('linux',)), ('postgresql', 'PostgreSQL', ('postgresql', 'postgres')), ('mysql', 'MySQL', ('mysql',)), ('sqlite', 'SQLite', ('sqlite',)), ('power-bi', 'Power BI', ('power bi', 'powerbi')), ('tableau', 'Tableau', ('tableau',)), ('excel', 'Excel', ('microsoft excel', 'excel')), ('kubernetes', 'Kubernetes', ('kubernetes', 'k8s')), ('aws', 'Amazon Web Services', ('amazon web services', 'aws')), ('azure', 'Microsoft Azure', ('microsoft azure', 'azure')), ('hugging-face-transformers', 'Hugging Face Transformers', ('hugging face transformers',)))

def query_rows(sql, parameters=(), *, database_path=None):
    connection = connect_database(database_path=database_path)
    try:
        cursor = connection.execute(sql, parameters)
        names = [item[0] for item in cursor.description]
        return [dict(zip(names, row)) for row in cursor.fetchall()]
    finally:
        connection.close()

def prepare_application(*, database_path=None):
    initialise_database(database_path=database_path)
    seed_skill_catalogue(database_path=database_path)
    seed_skill_aliases(database_path=database_path)
    for key, name, aliases in EXTRA_SKILLS:
        skill_id = get_or_create_skill(key, name, database_path=database_path)
        for alias in aliases:
            add_skill_alias(alias, skill_id, database_path=database_path)

def list_candidates(*, database_path=None):
    return query_rows('SELECT candidate_id, display_name FROM candidates ORDER BY candidate_id', database_path=database_path)

def list_skills(*, database_path=None):
    return query_rows('SELECT skill_id, skill_key, canonical_name, esco_uri FROM skills ORDER BY canonical_name COLLATE NOCASE', database_path=database_path)

def list_jobs(*, database_path=None):
    return query_rows('SELECT * FROM jobs ORDER BY job_id DESC', database_path=database_path)

def remove_candidate_skill(candidate_id, skill_id, *, database_path=None):
    if any((type(value) is not int or value <= 0 for value in (candidate_id, skill_id))):
        raise ValueError('Candidate and skill IDs must be positive integers.')
    connection = connect_database(database_path=database_path)
    try:
        connection.execute('DELETE FROM candidate_skills WHERE candidate_id = ? AND skill_id = ?', (candidate_id, skill_id))
        connection.commit()
    finally:
        connection.close()

def analyse_job(description_text, candidate_id, *, database_path=None):
    profile = {row['skill_id']: row for row in read_candidate_skills(candidate_id, database_path=database_path)}
    mentions = find_skill_mentions(description_text, database_path=database_path)
    result = []
    for mention in mentions:
        left, right = clause_bounds(description_text, mention['start'], mention['end'])
        clause = description_text[left:right]
        status, rule_id = interpret_mention(description_text, mention, mentions)
        entry = profile.get(mention['skill_id'])
        result.append({**mention, 'context_text': clause, 'context_start': left, 'context_end': right, 'requirement_status': status, 'rule_id': rule_id, 'profile_status': entry['evidence_status'] if entry else 'not_documented', 'profile_note': entry['evidence_note'] if entry else None})
    return result
