"""Trusted repository demo seed; isolated writable copies, no Streamlit dependency."""
from collections import Counter
from contextlib import closing
from pathlib import Path
import base64
import hashlib
import json
import sqlite3
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / 'demo' / 'workspace.sql'
REQUIRED = {'jobs', 'candidates', 'candidate_skills', 'skills', 'skill_aliases',
            'navigator_languages_v2', 'navigator_preferences_v3', 'navigator_metadata_v3',
            'navigator_reviews_v2'}

def quote(name):
    return '"' + name.replace('"', '""') + '"'

def cell(value):
    if isinstance(value, bytes):
        return {'sqlite_blob': base64.b64encode(value).decode('ascii')}
    return value

def logical_state(connection):
    tables = {}
    names = [r[0] for r in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    for name in names:
        columns = [r[1] for r in connection.execute('PRAGMA table_info(' + quote(name) + ')')]
        records = sorted(json.dumps([cell(v) for v in row], ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False)
                         for row in connection.execute('SELECT * FROM ' + quote(name)))
        tables[name] = {'columns': columns, 'records': records}
    return tables

def check(connection):
    result = connection.execute('PRAGMA integrity_check').fetchall()
    if result != [('ok',)]:
        raise ValueError('Database integrity check failed: ' + repr(result[:3]))
    missing = REQUIRED - set(logical_state(connection))
    if missing:
        raise ValueError('Missing workspace tables: ' + ', '.join(sorted(missing)))
    violations = connection.execute('PRAGMA foreign_key_check').fetchall()
    if violations:
        raise ValueError('Foreign-key errors: ' + repr(violations[:3]))

def describe(connection):
    state = logical_state(connection)
    tables = {name: {'rows': len(item['records']),
                     'content_sha256': hashlib.sha256(json.dumps(item, ensure_ascii=False,
                           separators=(',', ':')).encode('utf-8')).hexdigest()}
              for name, item in state.items()}
    profiles = [{'candidate_id': r[0], 'display_name': r[1]} for r in connection.execute(
        'SELECT candidate_id,display_name FROM candidates ORDER BY candidate_id')]
    languages = [list(r) for r in connection.execute(
        'SELECT candidate_id,language,reported_level,note FROM navigator_languages_v2 ORDER BY candidate_id,language')]
    return {'tables': tables, 'profiles': profiles, 'languages': languages}

def restore(sql, connection):
    connection.executescript(sql)
    connection.execute('PRAGMA foreign_keys=ON')
    check(connection)

def export_workspace(source, destination=SEED, overwrite=False):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    manifest = destination.with_suffix('.json')
    if not source.is_file():
        raise FileNotFoundError('Source database does not exist: ' + str(source))
    if source == destination or source == manifest:
        raise ValueError('Export must not replace the source database.')
    if not overwrite and (destination.exists() or manifest.exists()):
        raise FileExistsError('Demo seed exists. Use --replace only when deliberately refreshing it.')
    with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as original:
        with closing(sqlite3.connect(':memory:')) as snapshot:
            original.backup(snapshot)
            check(snapshot)
            sql = '\n'.join(snapshot.iterdump()) + '\n'
            before = logical_state(snapshot)
            description = describe(snapshot)
            with closing(sqlite3.connect(':memory:')) as restored:
                restore(sql, restored)
                if logical_state(restored) != before:
                    raise ValueError('Export round-trip did not preserve every table row.')
    data = sql.encode('utf-8')
    metadata = dict(format='jobfit-demo-sql-v1', sql_sha256=hashlib.sha256(data).hexdigest(),
                    **description)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    manifest.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return metadata

def open_workspace(initialise, seed_path=SEED):
    seed_path = Path(seed_path)
    if not seed_path.is_file():
        raise FileNotFoundError('Published demo seed missing. Run tools/export_demo.py before publishing.')
    data = seed_path.read_bytes()
    expected = json.loads(seed_path.with_suffix('.json').read_text(encoding='utf-8'))
    if expected.get('format') != 'jobfit-demo-sql-v1':
        raise ValueError('Unsupported demo seed manifest.')
    if hashlib.sha256(data).hexdigest() != expected['sql_sha256']:
        raise ValueError('Demo SQL and manifest differ. Export them together again.')
    handle = tempfile.TemporaryDirectory(prefix='jobfit-public-demo-')
    path = Path(handle.name) / 'workspace.db'
    try:
        with closing(sqlite3.connect(path)) as connection:
            restore(data.decode('utf-8'), connection)
            if describe(connection) != {k: expected[k] for k in ('tables', 'profiles', 'languages')}:
                raise ValueError('Restored workspace does not match its manifest.')
            before = logical_state(connection)
        initialise(path)
        with closing(sqlite3.connect(path)) as connection:
            check(connection)
            after = logical_state(connection)
            for name, item in before.items():
                if name not in after or item['columns'] != after[name]['columns']:
                    raise ValueError('Initialisation changed an existing table: ' + name)
                if Counter(item['records']) - Counter(after[name]['records']):
                    raise ValueError('Initialisation changed existing records: ' + name)
        return handle, path
    except Exception:
        handle.cleanup()
        raise
