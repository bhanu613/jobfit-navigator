"""Additive catalogue, preferences, metadata and language evidence services."""
import hashlib
import json
import re
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from .database import connect_database
from .navigator_interpretation import interpret_clause, clause_bounds
CATALOGUE = Path(__file__).parent / 'catalogue_v03.json'
PREFERENCE_FIELDS = ('role_areas', 'locations', 'work_types')
METADATA_FIELDS = ('company', 'location', 'work_type', 'source_language')

@contextmanager
def connection(path):
    c = connect_database(database_path=path)
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()

def initialise(path):
    with connection(path) as c:
        c.execute('CREATE TABLE IF NOT EXISTS navigator_catalogue_v3 (\n            version TEXT PRIMARY KEY, sha256 TEXT NOT NULL,\n            provenance TEXT NOT NULL, review_status TEXT NOT NULL, loaded_at TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS navigator_preferences_v3 (\n            candidate_id INTEGER PRIMARY KEY REFERENCES candidates(candidate_id) ON DELETE CASCADE,\n            payload TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS navigator_metadata_v3 (\n            job_id INTEGER PRIMARY KEY REFERENCES jobs(job_id) ON DELETE CASCADE,\n            company TEXT NOT NULL, location TEXT NOT NULL,\n            work_type TEXT NOT NULL, source_language TEXT NOT NULL)')

def validate_catalogue(data):
    if not isinstance(data, dict):
        raise ValueError('Catalogue must be an object.')
    for field in ('version', 'provenance', 'review_status'):
        if not isinstance(data.get(field), str) or not data[field].strip():
            raise ValueError('Missing catalogue metadata: ' + field)
    concepts = data.get('concepts')
    if not isinstance(concepts, list) or not concepts:
        raise ValueError('Catalogue needs a nonempty concept list.')
    keys, owners = (set(), {})
    for item in concepts:
        if not isinstance(item, dict):
            raise ValueError('Each concept must be an object.')
        key, name, aliases = (item.get('key'), item.get('name'), item.get('aliases'))
        if not isinstance(key, str) or not key.strip() or key != key.strip() or (key in keys):
            raise ValueError('Invalid or duplicate concept key.')
        keys.add(key)
        if not isinstance(name, str) or not name.strip() or name != name.strip():
            raise ValueError('Invalid canonical name.')
        if item.get('esco_uri') is not None:
            raise ValueError('This importer does not verify ESCO mappings; use null esco_uri.')
        if not isinstance(aliases, list) or not aliases:
            raise ValueError('Each concept needs aliases.')
        for alias in aliases:
            if not isinstance(alias, str) or not alias.strip():
                raise ValueError('Invalid alias.')
            normal = ' '.join(alias.lower().split())
            if normal in owners:
                raise ValueError('Duplicate normalised alias: ' + normal)
            owners[normal] = key
    return concepts

def load_catalogue(path, filename=CATALOGUE):
    data = json.loads(Path(filename).read_text(encoding='utf-8'))
    concepts = validate_catalogue(data)
    digest = hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
    with connection(path) as c:
        previous = c.execute('SELECT sha256 FROM navigator_catalogue_v3 WHERE version=?', (data['version'],)).fetchone()
        if previous and previous[0] != digest:
            raise ValueError('Catalogue content changed without changing its version.')
        for item in concepts:
            c.execute('INSERT INTO skills(skill_key,canonical_name) VALUES(?,?) ON CONFLICT(skill_key) DO NOTHING', (item['key'], item['name']))
            skill_id, name = c.execute('SELECT skill_id,canonical_name FROM skills WHERE skill_key=?', (item['key'],)).fetchone()
            if name != item['name']:
                raise ValueError('Existing canonical name conflict: ' + item['key'])
            for alias in item['aliases']:
                alias = ' '.join(alias.lower().split())
                c.execute('INSERT INTO skill_aliases(alias,skill_id) VALUES(?,?) ON CONFLICT(alias) DO NOTHING', (alias, skill_id))
                if c.execute('SELECT skill_id FROM skill_aliases WHERE alias=?', (alias,)).fetchone()[0] != skill_id:
                    raise ValueError('Existing alias conflict: ' + alias)
        c.execute('INSERT INTO navigator_catalogue_v3 VALUES(?,?,?,?,?) ON CONFLICT(version) DO NOTHING', (data['version'], digest, data['provenance'], data['review_status'], datetime.now(timezone.utc).isoformat()))
    return dict(version=data['version'], sha256=digest, concept_count=len(concepts), provenance=data['provenance'], review_status=data['review_status'], import_policy='Additive; existing aliases outside this file remain active.')

def require_positive_id(value):
    if type(value) is not int or value <= 0:
        raise ValueError('ID must be a positive integer.')

def save_preferences(path, candidate_id, values):
    require_positive_id(candidate_id)
    if not isinstance(values, dict) or set(values) != set(PREFERENCE_FIELDS):
        raise ValueError('Expected role_areas, locations and work_types.')
    clean = {}
    for field in PREFERENCE_FIELDS:
        items = values[field]
        if not isinstance(items, list) or any((not isinstance(x, str) or not x.strip() for x in items)):
            raise ValueError('Preferences must be lists of nonblank text.')
        clean[field] = list(dict.fromkeys((x.strip() for x in items)))
    with connection(path) as c:
        c.execute('INSERT INTO navigator_preferences_v3 VALUES(?,?) ON CONFLICT(candidate_id) DO UPDATE SET payload=excluded.payload', (candidate_id, json.dumps(clean, ensure_ascii=False)))

def get_preferences(path, candidate_id):
    require_positive_id(candidate_id)
    with connection(path) as c:
        row = c.execute('SELECT payload FROM navigator_preferences_v3 WHERE candidate_id=?', (candidate_id,)).fetchone()
    return json.loads(row[0]) if row else {key: [] for key in PREFERENCE_FIELDS}

def save_metadata(path, job_id, values):
    require_positive_id(job_id)
    if not isinstance(values, dict) or set(values) != set(METADATA_FIELDS) or any((not isinstance(v, str) for v in values.values())):
        raise ValueError('Expected the four metadata text fields.')
    with connection(path) as c:
        c.execute('INSERT INTO navigator_metadata_v3 VALUES(?,?,?,?,?) ON CONFLICT(job_id)\n                  DO UPDATE SET company=excluded.company,location=excluded.location,\n                  work_type=excluded.work_type,source_language=excluded.source_language', (job_id, *(values[k].strip() for k in METADATA_FIELDS)))

def get_metadata(path, job_id):
    require_positive_id(job_id)
    with connection(path) as c:
        row = c.execute('SELECT company,location,work_type,source_language FROM navigator_metadata_v3 WHERE job_id=?', (job_id,)).fetchone()
    return dict(zip(METADATA_FIELDS, row)) if row else {key: '' for key in METADATA_FIELDS}
LANGUAGE_ALIASES = {'German': ('german', 'deutsch', 'deutschkenntnisse'), 'English': ('english', 'englisch', 'englischkenntnisse'), 'French': ('french', 'französisch', 'französischkenntnisse'), 'Spanish': ('spanish', 'spanisch', 'spanischkenntnisse')}
LEVEL = re.compile('\\b[ABC][12]\\b', re.I)
QUALITATIVE = re.compile('\\b(?:fluent|native|good|excellent|fließend|fliessend|verhandlungssicher|gute[nrms]?)\\b', re.I)

def analyse_languages(text, profile_languages=()):
    if not isinstance(text, str) or not text.strip():
        raise ValueError('Description must be nonblank text.')
    profile = {row['language']: row for row in profile_languages}
    mentions = []
    for language, aliases in LANGUAGE_ALIASES.items():
        pattern = re.compile('(?<!\\w)(?:' + '|'.join((re.escape(x) for x in sorted(aliases, key=len, reverse=True))) + ')(?!\\w)', re.I)
        for match in pattern.finditer(text):
            mentions.append((match.start(), match.end(), language, match.group()))
    mentions.sort()
    rows = []
    for start, end, language, wording in mentions:
        left, right = clause_bounds(text, start, end)
        clause = text[left:right]
        shared = len({m[2] for m in mentions if left <= m[0] and m[1] <= right}) > 1
        status, rule = interpret_clause(clause, shared_scope=shared)
        levels = list(dict.fromkeys((m.group().upper() for m in LEVEL.finditer(clause))))
        candidate = levels[0] if len(levels) == 1 and (not shared) else None
        notes = []
        if shared:
            notes.append('Multiple languages share context; scope and levels need review.')
        if len(levels) > 1:
            notes.append('Multiple CEFR tokens; no single level assigned.')
        if QUALITATIVE.search(clause):
            notes.append('Qualitative wording is preserved, not converted to CEFR.')
        if candidate:
            notes.append('Same-clause CEFR candidate only; verify its linkage and meaning manually.')
        entry = profile.get(language)
        rows.append(dict(language=language, matched_text=wording, start=start, end=end, context_text=clause, context_start=left, context_end=right, requirement_status=status, rule_id=rule, cefr_candidate=candidate, profile_level=entry['reported_level'] if entry else 'not_documented', profile_note=entry.get('note', '') if entry else '', comparison='human_review_required', review_notes=notes))
    return rows

def augment_report(report, catalogue, metadata, preferences, language_rows):
    result = dict(report)
    result.update(format_version='jobfit-analysis-0.3', catalogue=catalogue, job_metadata=metadata, search_preferences=preferences, language_mentions=language_rows)
    result['legacy_v2_limitations'] = report.get('limitations', [])
    result['limitations'] = ['Bounded technical rules and alias catalogue can miss or misinterpret requirements.']
    result['limitations'] += ['Language extraction is bounded; CEFR candidates and all proficiency comparisons require human review.', 'Catalogue is project-authored and draft, with no verified ESCO mappings.', 'Preferences are stored but not yet used for retrieval. Corpus insights and independent evaluation are pending.', 'Technical reviews remain separate; language review persistence is not implemented.']
    return result
