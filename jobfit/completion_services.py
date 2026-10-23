"""Local completion workspace services. All mutations are explicit and audited."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import csv
import hashlib
import io
import json
import re
import sqlite3
import tempfile
import uuid
STATUSES = ('required', 'desirable', 'not_required', 'uncertain')
TABLES = ('completion_alias_state', 'completion_esco', 'completion_language_reviews', 'completion_events')

def now():
    return datetime.now(timezone.utc).isoformat()

def normal(value):
    return ' '.join(value.casefold().split())

def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def positive(value, name='ID'):
    if type(value) is not int or value <= 0:
        raise ValueError(name + ' must be a positive integer.')
    return value

def reason_text(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('A nonblank rationale is required.')
    return value.strip()

@contextmanager
def connect(path, write=False):
    p = Path(path).resolve()
    if not p.is_file():
        raise ValueError('Existing database required; no implicit database creation.')
    c = sqlite3.connect(p.as_uri() + ('?mode=rw' if write else '?mode=ro'), uri=True, timeout=20)
    c.row_factory = sqlite3.Row
    try:
        c.execute('PRAGMA foreign_keys=ON')
        if write:
            c.execute('BEGIN IMMEDIATE')
        yield c
        if write:
            c.commit()
    except Exception:
        if write:
            c.rollback()
        raise
    finally:
        c.close()

def initialise(path):
    with connect(path, True) as c:
        required = {'jobs': {'job_id', 'title', 'description_text'}, 'skills': {'skill_id', 'skill_key', 'canonical_name'}, 'skill_aliases': {'alias', 'skill_id'}, 'candidates': {'candidate_id', 'display_name'}, 'candidate_skills': {'candidate_id', 'skill_id', 'evidence_status', 'evidence_note'}}
        for table, columns in required.items():
            present = {r['name'] for r in c.execute('PRAGMA table_info(' + table + ')')}
            if not columns <= present:
                raise ValueError('Incompatible database schema: ' + table)
        c.execute('CREATE TABLE IF NOT EXISTS completion_alias_state(alias TEXT PRIMARY KEY,skill_id INTEGER NOT NULL REFERENCES skills(skill_id),active INTEGER NOT NULL CHECK(active IN(0,1)),reason TEXT NOT NULL,changed_at TEXT NOT NULL)')
        c.execute("CREATE TABLE IF NOT EXISTS completion_esco(skill_id INTEGER PRIMARY KEY REFERENCES skills(skill_id),uri TEXT NOT NULL,preferred_label TEXT NOT NULL,classification_version TEXT NOT NULL,language TEXT NOT NULL,source_url TEXT NOT NULL,file_sha256 TEXT NOT NULL,source_row_json TEXT NOT NULL,relation TEXT NOT NULL CHECK(relation IN('exact','broader','related')),reason TEXT NOT NULL,mapped_at TEXT NOT NULL)")
        c.execute("CREATE TABLE IF NOT EXISTS completion_language_reviews(job_id INTEGER NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,source_hash TEXT NOT NULL,language TEXT NOT NULL,start_offset INTEGER NOT NULL,end_offset INTEGER NOT NULL,status TEXT NOT NULL CHECK(status IN('required','desirable','not_required','uncertain')),reason TEXT NOT NULL,automatic_json TEXT NOT NULL,reviewed_at TEXT NOT NULL,PRIMARY KEY(job_id,source_hash,language,start_offset,end_offset))")
        c.execute('CREATE TABLE IF NOT EXISTS completion_events(event_id INTEGER PRIMARY KEY,event_type TEXT NOT NULL,payload_json TEXT NOT NULL,created_at TEXT NOT NULL)')

def event(c, kind, payload):
    c.execute('INSERT INTO completion_events(event_type,payload_json,created_at) VALUES(?,?,?)', (kind, json.dumps(payload, ensure_ascii=False, sort_keys=True), now()))

def candidates(path):
    with connect(path) as c:
        return [dict(r) for r in c.execute('SELECT candidate_id,display_name FROM candidates ORDER BY candidate_id')]

def jobs(path):
    with connect(path) as c:
        return [dict(r) for r in c.execute('SELECT job_id,title,description_text FROM jobs ORDER BY job_id')]

def retired(path):
    with connect(path) as c:
        if not c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='completion_alias_state'").fetchone():
            return set()
        return {(normal(r['alias']), r['skill_id']) for r in c.execute('SELECT alias,skill_id FROM completion_alias_state WHERE active=0')}

def vocabulary(path):
    with connect(path) as c:
        rows = [dict(r) for r in c.execute('SELECT s.skill_id,s.skill_key,s.canonical_name,a.alias FROM skills s LEFT JOIN skill_aliases a ON a.skill_id=s.skill_id ORDER BY s.canonical_name,a.alias')]
        state = {(normal(r['alias']), r['skill_id']): dict(r) for r in c.execute('SELECT * FROM completion_alias_state')}
        external = {r['skill_id']: dict(r) for r in c.execute('SELECT * FROM completion_esco')}
    for r in rows:
        r.update(active=bool(state.get((normal(r['alias']), r['skill_id']), {}).get('active', 1)) if r['alias'] else False, external_mapping=external.get(r['skill_id']))
    return rows

def change_alias(path, skill_id, alias, active, reason):
    positive(skill_id, 'Concept ID')
    reason = reason_text(reason)
    if type(active) is not bool:
        raise ValueError('Alias active flag must be boolean.')
    if not isinstance(alias, str) or not normal(alias) or len(alias) > 200:
        raise ValueError('Alias must be nonblank and at most 200 characters.')
    alias = normal(alias)
    with connect(path, True) as c:
        if not c.execute('SELECT 1 FROM skills WHERE skill_id=?', (skill_id,)).fetchone():
            raise ValueError('Unknown concept.')
        owners = [r for r in c.execute('SELECT alias,skill_id FROM skill_aliases') if normal(r['alias']) == alias]
        if any((r['skill_id'] != skill_id for r in owners)):
            raise ValueError('Alias already identifies a different concept; reassignment refused.')
        if not owners:
            if not active:
                raise ValueError('Cannot retire an unknown alias.')
            c.execute('INSERT INTO skill_aliases(alias,skill_id) VALUES(?,?)', (alias, skill_id))
        c.execute('INSERT INTO completion_alias_state VALUES(?,?,?,?,?) ON CONFLICT(alias) DO UPDATE SET active=excluded.active,reason=excluded.reason,changed_at=excluded.changed_at', (alias, skill_id, int(active), reason, now()))
        event(c, 'alias_change', dict(alias=alias, skill_id=skill_id, active=active, reason=reason))

def find_active_mentions(text, *, database_path):
    if not isinstance(text, str) or not text.strip():
        raise ValueError('Description must be nonblank text.')
    excluded = retired(database_path)
    with connect(database_path) as c:
        aliases = c.execute('SELECT a.alias,s.skill_id,s.skill_key,s.canonical_name FROM skill_aliases a JOIN skills s ON s.skill_id=a.skill_id ORDER BY a.alias').fetchall()
    candidates = []
    for alias, sid, key, name in aliases:
        if (normal(alias), sid) in excluded:
            continue
        pattern = re.compile('(?<!\\w)' + '\\s+'.join((re.escape(s) for s in alias.split())) + '(?!\\w)', re.I)
        for m in pattern.finditer(text):
            start, end = m.span()
            left = text.rfind('\n', 0, start) + 1
            right = text.find('\n', end)
            right = len(text) if right < 0 else right
            candidates.append(dict(skill_id=sid, skill_key=key, canonical_name=name, matched_alias=alias, matched_text=m.group(), start=start, end=end, evidence_text=text[left:right], evidence_start=left, evidence_end=right))
    candidates.sort(key=lambda r: (-(r['end'] - r['start']), r['start'], r['matched_alias']))
    result = []
    for row in candidates:
        if not any((row['start'] < other['end'] and other['start'] < row['end'] for other in result)):
            result.append(row)
    return sorted(result, key=lambda r: (r['start'], r['end']))

def parse_esco(raw):
    if not isinstance(raw, bytes) or not raw or len(raw) > 40000000:
        raise ValueError('Expected nonempty UTF-8 CSV, maximum 40 MB.')
    text = raw.decode('utf-8-sig')
    head = text.splitlines()[0]
    delimiter = ';' if head.count(';') > head.count(',') else ','
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames) or (not {'conceptUri', 'preferredLabel'}.issubset(reader.fieldnames)):
        raise ValueError('Expected unique ESCO CSV columns including conceptUri and preferredLabel.')
    rows = {}
    for row in reader:
        if None in row:
            raise ValueError('Malformed CSV row: unexpected fields.')
        uri = (row.get('conceptUri') or '').strip()
        label = (row.get('preferredLabel') or '').strip()
        if not re.fullmatch('https?://data\\.europa\\.eu/esco/skill/[0-9a-fA-F-]{36}', uri) or not label:
            raise ValueError('Invalid ESCO skill URI or blank preferred label.')
        uuid.UUID(uri.rsplit('/', 1)[1])
        if uri in rows:
            raise ValueError('Duplicate URI; use a single-language skills CSV.')
        rows[uri] = row
    if not rows:
        raise ValueError('CSV has no skill rows.')
    return dict(file_sha256=hashlib.sha256(raw).hexdigest(), rows=rows)

def save_mapping(path, skill_id, uri, parsed, version, language, source_url, relation, reason):
    positive(skill_id, 'Concept ID')
    reason = reason_text(reason)
    if relation not in ('exact', 'broader', 'related') or uri not in parsed['rows']:
        raise ValueError('Choose a source-file URI and explicit relation.')
    if not isinstance(version, str) or not version.strip() or (not isinstance(language, str)) or (not language.strip()):
        raise ValueError('Classification version and language required.')
    if not isinstance(source_url, str) or not re.match('^https://(?:esco\\.ec\\.europa\\.eu|ec\\.europa\\.eu)(?:/|$)', source_url):
        raise ValueError('Official ESCO source-page URL required.')
    row = parsed['rows'][uri]
    with connect(path, True) as c:
        if not c.execute('SELECT 1 FROM skills WHERE skill_id=?', (skill_id,)).fetchone():
            raise ValueError('Unknown local concept.')
        c.execute('INSERT INTO completion_esco VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(skill_id) DO UPDATE SET uri=excluded.uri,preferred_label=excluded.preferred_label,classification_version=excluded.classification_version,language=excluded.language,source_url=excluded.source_url,file_sha256=excluded.file_sha256,source_row_json=excluded.source_row_json,relation=excluded.relation,reason=excluded.reason,mapped_at=excluded.mapped_at', (skill_id, uri, row['preferredLabel'], version.strip(), language.strip(), source_url, parsed['file_sha256'], json.dumps(row, ensure_ascii=False), relation, reason, now()))
        event(c, 'esco_mapping', dict(skill_id=skill_id, uri=uri, relation=relation, file_sha256=parsed['file_sha256'], reason=reason))

def languages(path, job_id):
    positive(job_id, 'Job ID')
    from .navigator_broader import analyse_languages
    with connect(path) as c:
        job = c.execute('SELECT description_text FROM jobs WHERE job_id=?', (job_id,)).fetchone()
        if job is None:
            raise ValueError('Job not found.')
        text = job[0]
        reviews = {(r['language'], r['start_offset'], r['end_offset']): dict(r) for r in c.execute('SELECT * FROM completion_language_reviews WHERE job_id=? AND source_hash=?', (job_id, digest(text)))}
    rows = analyse_languages(text, ()) if text.strip() else []
    for row in rows:
        review = reviews.get((row['language'], row['start'], row['end']))
        automatic = dict(status=row['requirement_status'], rule_id=row.get('rule_id'), cefr_candidate=row.get('cefr_candidate'))
        row.update(saved_review=review, effective_status=review['status'] if review else row['requirement_status'], review_drift=bool(review and json.loads(review['automatic_json']) != automatic))
    return (text, rows)

def save_language_review(path, job_id, source, language, start, end, status, reason):
    positive(job_id, 'Job ID')
    reason = reason_text(reason)
    if status not in STATUSES:
        raise ValueError('Invalid status.')
    text, rows = languages(path, job_id)
    if source != text:
        raise ValueError('Source changed; reload before reviewing.')
    row = next((r for r in rows if r['language'] == language and r['start'] == start and (r['end'] == end)), None)
    if row is None:
        raise ValueError('Review span must exactly match a detected language mention.')
    automatic = json.dumps(dict(status=row['requirement_status'], rule_id=row.get('rule_id'), cefr_candidate=row.get('cefr_candidate')), sort_keys=True)
    with connect(path, True) as c:
        current = c.execute('SELECT description_text FROM jobs WHERE job_id=?', (job_id,)).fetchone()
        if current is None or current[0] != source:
            raise ValueError('Source changed while saving.')
        c.execute('INSERT INTO completion_language_reviews(job_id,source_hash,language,start_offset,end_offset,status,reason,automatic_json,reviewed_at) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(job_id,source_hash,language,start_offset,end_offset) DO UPDATE SET status=excluded.status,reason=excluded.reason,automatic_json=excluded.automatic_json,reviewed_at=excluded.reviewed_at', (job_id, digest(source), language, start, end, status, reason, automatic, now()))
        event(c, 'language_review', dict(job_id=job_id, source_hash=digest(source), language=language, start=start, end=end, status=status))

def remove_language_review(path, job_id, source, language, start, end):
    positive(job_id, 'Job ID')
    with connect(path, True) as c:
        c.execute('DELETE FROM completion_language_reviews WHERE job_id=? AND source_hash=? AND language=? AND start_offset=? AND end_offset=?', (job_id, digest(source), language, start, end))
        event(c, 'language_review_removed', dict(job_id=job_id, source_hash=digest(source), language=language, start=start, end=end))

def _language_corpus(path):
    counts = {}
    evidence = []
    records = jobs(path)
    for job in records:
        _, rows = languages(path, job['job_id'])
        seen = {}
        for row in rows:
            s = seen.setdefault(row['language'], dict(automatic=set(), effective=set()))
            s['automatic'].add(row['requirement_status'])
            s['effective'].add(row['effective_status'])
            evidence.append(dict(job_id=job['job_id'], title=job['title'], **row))
        for language, s in seen.items():
            out = counts.setdefault(language, dict(language=language, jobs_with_mention=0, automatic={k: 0 for k in STATUSES}, effective={k: 0 for k in STATUSES}))
            out['jobs_with_mention'] += 1
            for kind in ('automatic', 'effective'):
                for k in s[kind]:
                    out[kind][k] += 1
    return dict(saved_jobs=len(records), counts=list(counts.values()), evidence=evidence)

@contextmanager
def snapshot(path):
    with tempfile.TemporaryDirectory() as d:
        target = Path(d) / 'snapshot.db'
        with connect(path) as source:
            dest = sqlite3.connect(target)
            try:
                source.backup(dest)
            finally:
                dest.close()
        yield target

def language_corpus(path):
    with snapshot(path) as p:
        result = _language_corpus(p)
    return dict(**result, generated_at=now(), scope='Consistent SQLite snapshot. Bounded language detector; separate status reviews, no CEFR override or qualification inference. Non-exclusive per-job/status counts.')

def technical_corpus(path, candidate_id):
    positive(candidate_id, 'Candidate ID')
    from .navigator_service import analyse_job
    with snapshot(path) as p:
        counts = {}
        evidence = []
        records = jobs(p)
        skipped = []
        with connect(p) as c:
            if not c.execute('SELECT 1 FROM candidates WHERE candidate_id=?', (candidate_id,)).fetchone():
                raise ValueError('Candidate not found.')
        for job in records:
            if not job['description_text'].strip():
                skipped.append(job['job_id'])
                continue
            rows = analyse_job(job['description_text'], candidate_id, database_path=p)
            seen = {}
            for row in rows:
                seen.setdefault(row['skill_id'], set()).add(row['requirement_status'])
                evidence.append(dict(job_id=job['job_id'], title=job['title'], **row))
                counts.setdefault(row['skill_id'], dict(skill_id=row['skill_id'], canonical_name=row['canonical_name'], jobs_with_mention=0, automatic={k: 0 for k in STATUSES}))
            for sid, statuses in seen.items():
                counts[sid]['jobs_with_mention'] += 1
                for status in statuses:
                    counts[sid]['automatic'][status] += 1
    return dict(saved_jobs=len(records), skipped_blank_jobs=skipped, counts=sorted(counts.values(), key=lambda r: (-r['jobs_with_mention'], r['canonical_name'])), evidence=evidence, generated_at=now(), scope='Consistent SQLite snapshot. AUTOMATIC technical statuses only; saved technical reviews are not applied here. Existing integrated collection workspace retains its automatic/effective comparison. Counts non-exclusive per-job/status, not vacancy prevalence or candidate qualification.')

def profile_search(path, candidate_id, categories, limit=20):
    positive(candidate_id, 'Candidate ID')
    positive(limit, 'Limit')
    if not categories or not set(categories) <= {'evidenced', 'developing', 'self_reported'}:
        raise ValueError('Choose explicit valid documentation categories.')
    from .navigator_search import rank_jobs
    with snapshot(path) as p:
        with connect(p) as c:
            if not c.execute('SELECT 1 FROM candidates WHERE candidate_id=?', (candidate_id,)).fetchone():
                raise ValueError('Candidate not found.')
            profile = [dict(r) for r in c.execute('SELECT s.skill_id,s.canonical_name,cs.evidence_status,cs.evidence_note FROM candidate_skills cs JOIN skills s ON s.skill_id=cs.skill_id WHERE cs.candidate_id=? ORDER BY s.skill_id', (candidate_id,)) if r['evidence_status'] in categories]
        query = ' '.join((r['canonical_name'] for r in profile))
        results = rank_jobs(jobs(p), query, limit=limit) if query else []
    return dict(candidate_id=candidate_id, query=query, profile_records=profile, results=results, scope='Selected profile labels form a visible OR lexical BM25 query. Consistent SQLite snapshot. Multiword labels tokenise, no exact concept satisfaction or suitability claim. Developing/self-reported records opt-in; no location or preference filter, semantic entailment or proficiency inference.')

def state_export(path):
    with connect(path) as c:
        c.execute('BEGIN')
        return {t: [dict(r) for r in c.execute('SELECT * FROM ' + t)] for t in TABLES}

def health(path):
    with connect(path) as c:
        c.execute('BEGIN')
        quick = c.execute('PRAGMA quick_check').fetchone()[0]
        foreign = [list(r) for r in c.execute('PRAGMA foreign_key_check')]
        counts = {t: c.execute('SELECT COUNT(*) FROM ' + t).fetchone()[0] for t in ('jobs', 'skills', 'skill_aliases') + TABLES}
    return dict(sqlite_quick_check=quick, foreign_key_violations=foreign, counts=counts)

def csv_bytes(rows):
    if not rows:
        return b''
    columns = list(dict.fromkeys((k for row in rows for k in row)))
    out = io.StringIO()
    w = csv.DictWriter(out, columns)
    w.writeheader()
    for row in rows:
        clean = {}
        for k, v in row.items():
            value = json.dumps(v, ensure_ascii=False, sort_keys=True) if isinstance(v, (dict, list)) else '' if v is None else str(v)
            if value.lstrip().startswith(('=', '+', '-', '@')):
                value = "'" + value
            clean[k] = value
        w.writerow(clean)
    return out.getvalue().encode('utf-8-sig')
