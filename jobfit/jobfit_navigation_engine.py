"""Candidate navigation pipeline. Read-only existing data, explicit rules, no fit score."""
from pathlib import Path
from contextlib import contextmanager
from collections import Counter
import sqlite3
import tempfile
import re
import json
import hashlib
import math
VERSION = 'navigation-release-candidate-20261019'
MODEL = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
REVISION = 'e8f8c211226b894fcb81acc59f3b34ba3efd5f42'
STATES = ('required', 'desirable', 'not_required', 'uncertain')

def sha(t):
    return hashlib.sha256(t.encode()).hexdigest()

@contextmanager
def snapshot(path):
    p = Path(path).resolve()
    if not p.is_file():
        raise ValueError('Existing database required.')
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / 'snapshot.db'
        src = sqlite3.connect(p.as_uri() + '?mode=ro', uri=True)
        target = sqlite3.connect(dest)
        try:
            src.backup(target)
        finally:
            src.close()
            target.close()
        yield dest

def aggregate(states):
    s = set(states)
    if not s or not s <= set(STATES) or 'uncertain' in s or (len(s) > 1):
        return 'uncertain'
    return 'required' if 'required' in s else 'desirable' if 'desirable' in s else 'not_required'

def interpret(text, m, mentions):
    from .navigator_interpretation import interpret_mention, interpret_clause, clause_bounds
    legacy = interpret_mention(text, m, mentions)
    if legacy[0] != 'uncertain':
        return legacy
    left, right = clause_bounds(text, m['start'], m['end'])
    local = sorted([x for x in mentions if left <= x['start'] and x['end'] <= right], key=lambda x: x['start'])
    clause = text[left:right]
    if len(local) > 1 and (not re.search('\\b(?:or|oder|unless|except|not only|nicht nur)\\b', clause, re.I)):
        index = next((i for i, x in enumerate(local) if x['start'] == m['start'] and x['end'] == m['end']))
        a = m['start']
        b = local[index + 1]['start'] if index + 1 < len(local) else right
        segment = text[a:b]
        segment = re.sub('\\b(?:and|und|but|aber)\\s*$', '', segment, flags=re.I)
        pieces = []
        for i, x in enumerate(local):
            stop = local[i + 1]['start'] if i + 1 < len(local) else right
            piece = re.sub('\\b(?:and|und|but|aber)\\s*$', '', text[x['start']:stop], flags=re.I)
            status, rule = interpret_clause(piece)
            if not re.search('\\b(?:is|are|ist|sind)\\b', piece, re.I) or status == 'uncertain':
                break
            pieces.append(status)
        if len(pieces) == len(local):
            return (pieces[index], 'explicit_repeated_predicate_v1')
    line_start = text.rfind('\n', 0, m['start']) + 1
    line_end = text.find('\n', m['end'])
    line_end = len(text) if line_end < 0 else line_end
    current = text[line_start:line_end]
    line_mentions = [x for x in mentions if line_start <= x['start'] and x['end'] <= line_end]
    residue = current
    for x in sorted(line_mentions, key=lambda x: x['start'], reverse=True):
        residue = residue[:x['start'] - line_start] + residue[x['end'] - line_start:]
    if not residue.strip(' \t-*•,:/&'):
        for previous in reversed(text[:line_start].splitlines()[-8:]):
            head = previous.strip()
            if not head:
                break
            if re.fullmatch('(?:required skills|mandatory skills|requirements|erforderliche kenntnisse)\\s*:', head, re.I):
                return ('required', 'bounded_heading_v1')
            if re.fullmatch('(?:nice to have|desirable skills|optional skills|wünschenswert)\\s*:', head, re.I):
                return ('desirable', 'bounded_heading_v1')
            if not any((x['matched_text'].casefold() in head.casefold() for x in mentions)):
                break
    if len(local) == 1 and re.fullmatch('\\s*(?:you\\s+)?need\\s+not\\s+(?:know|have|use)\\s+' + re.escape(m['matched_text']) + '\\s*', clause, re.I):
        return ('not_required', 'explicit_need_not_v1')
    return legacy

def read(path):
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    try:
        known = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        names = ['jobs', 'skills', 'candidate_skills', 'candidates', 'navigator_reviews_v2', 'navigator_languages_v2', 'jf_batch_language', 'navigator_preferences_v3', 'navigator_metadata_v3']
        return {n: [dict(r) for r in c.execute('SELECT * FROM ' + n)] if n in known else [] for n in names}
    finally:
        c.close()

def candidate_report(path, cid):
    if type(cid) is not int or cid < 1:
        raise ValueError('Positive candidate ID required.')
    from .skill_mentions import find_skill_mentions
    from .navigator_broader import analyse_languages
    with snapshot(path) as p:
        data = read(p)
        if cid not in {r['candidate_id'] for r in data['candidates']}:
            raise ValueError('Candidate missing.')
        profile = {r['skill_id']: r for r in data['candidate_skills'] if r['candidate_id'] == cid}
        lang = [r for r in data['navigator_languages_v2'] if r['candidate_id'] == cid]
        reports = []
        corpus = {}
        lang_corpus = {}
        pref = next((json.loads(r['payload']) for r in data['navigator_preferences_v3'] if r['candidate_id'] == cid), dict(role_areas=[], locations=[], work_types=[]))
        metadata = {r['job_id']: r for r in data['navigator_metadata_v3']}
        for job in sorted(data['jobs'], key=lambda x: x['job_id']):
            text = job['description_text']
            digest = sha(text)
            mentions = find_skill_mentions(text, database_path=p) if text.strip() else []
            groups = {}
            reviews = {(r['skill_id'], r['start_offset'], r['end_offset']): r for r in data['navigator_reviews_v2'] if r['job_id'] == job['job_id'] and r['source_hash'] == digest}
            for m in mentions:
                if text[m['start']:m['end']] != m['matched_text']:
                    raise ValueError('Invalid extraction offsets.')
                status, rule = interpret(text, m, mentions)
                review = reviews.get((m['skill_id'], m['start'], m['end']))
                effective = review['reviewed_status'] if review else status
                entry = profile.get(m['skill_id'])
                row = dict(m, automatic_status=status, rule_id=rule, effective_status=effective, review=review, profile_status=entry['evidence_status'] if entry else 'not_documented', profile_note=entry['evidence_note'] if entry else None, review_rule_changed=bool(review and (review['rule_id_at_review'] != rule or review['rule_status_at_review'] != status)))
                groups.setdefault(m['skill_id'], []).append(row)
            concepts = []
            for sid, rows in groups.items():
                effective = aggregate((r['effective_status'] for r in rows))
                automatic = aggregate((r['automatic_status'] for r in rows))
                first = rows[0]
                category = first['profile_status']
                item = dict(skill_id=sid, canonical_name=first['canonical_name'], automatic_status=automatic, effective_status=effective, profile_status=category, profile_note=first['profile_note'], evidence=rows, mixed_wording=len({r["effective_status"] for r in rows})>1)
                concepts.append(item)
                c = corpus.setdefault(sid, dict(skill_id=sid, concept=first['canonical_name'], profile_status=category, required_jobs=[], desirable_jobs=[], review_jobs=[], not_required_jobs=[]))
                field = {'required': 'required_jobs', 'desirable': 'desirable_jobs', 'uncertain': 'review_jobs', 'not_required': 'not_required_jobs'}.get(effective)
                if field:
                    c[field].append(job['job_id'])
            languages = analyse_languages(text, lang) if text.strip() else []
            from .language_reviews import apply
            lc=sqlite3.connect(p)
            try:languages=apply(lc,job['job_id'],text,languages)
            finally:lc.close()
            for language in {l['language'] for l in languages}:
                group = [l for l in languages if l['language'] == language]
                status = aggregate((l['effective_status'] for l in group))
                v = lang_corpus.setdefault(language, dict(language=language, required_jobs=[], desirable_jobs=[], review_jobs=[], not_required_jobs=[]))
                field = {'required': 'required_jobs', 'desirable': 'desirable_jobs', 'uncertain': 'review_jobs', 'not_required': 'not_required_jobs'}.get(status)
                if field:
                    v[field].append(job['job_id'])
            actions = []
            for x in concepts:
                state = x['effective_status']
                document = x['profile_status']
                if state == 'required' and document != 'evidenced':
                    actions.append(dict(kind='document_or_develop', concept=x['canonical_name'], reason=f'Required in text; current documentation: {document}. Add genuine evidence or consider development; not proof of inability.'))
                elif state == 'required':
                    actions.append(dict(kind='tailor_evidence', concept=x['canonical_name'], reason='Required concept has an evidence note; review depth and tailor application, no eligibility conclusion.'))
                elif state == 'uncertain':
                    actions.append(dict(kind='review_requirement', concept=x['canonical_name'], reason='Scope or wording uncertain; inspect exact text before prioritising.'))
                elif state == 'desirable' and document != 'evidenced':
                    actions.append(dict(kind='optional_development', concept=x['canonical_name'], reason='Desirable, not mandatory; lower-priority documentation/development consideration.'))
            if any((x['effective_status'] != 'not_required' for x in languages)):
                actions.append(dict(kind='review_language', concept='Languages', reason='Compare exact language wording with your statement manually; no automatic proficiency/eligibility conclusion.'))
            reports.append(dict(job=job, source_hash=digest, metadata=metadata.get(job['job_id'], {}), concepts=concepts, languages=languages, actions=actions))
        priorities = sorted(corpus.values(), key=lambda x: (-len(x['required_jobs']), -len(x['desirable_jobs']), x['concept'].casefold()))
        for x in priorities:
            x['next_action'] = ('Tailor existing evidence' if x['profile_status']=='evidenced' else 'Check genuine evidence or development needs') if x['required_jobs'] else 'Review wording first' if x['review_jobs'] else 'Optional preparation only' if x['desirable_jobs'] else 'No required-skill action inferred'
        return dict(version=VERSION, candidate_id=cid, preferences=pref, profile=[dict(r,canonical_name=next(s['canonical_name'] for s in data['skills'] if s['skill_id']==r['skill_id'])) for r in profile.values()], profile_languages=lang, jobs=reports, priorities=priorities, language_priorities=list(lang_corpus.values()), scope='Current profile. Exact source evidence only; retrieval is separate. Source-bound technical reviews and reconciled language ledgers; conflicts require explicit review. Exclusive concept status aggregation; uncertain dominates. Priorities descriptive of saved corpus, not market prevalence or a recommendation to abandon/apply for a job. No verified ESCO expansion in this release.')

def normal(x):
    return ' '.join((x or '').casefold().split())

def load_encoder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL, revision=REVISION)

def search(report, query, *, categories=(), roles=False, locations=False, work_types=False, unknown=True, mode='BM25', encoder=None, limit=10):
    from .navigator_search import rank_jobs
    if mode not in ('BM25', 'Semantic', 'Hybrid'):
        raise ValueError('Unsupported mode.')
    if type(limit) is not int or limit < 1:
        raise ValueError('Positive limit required.')
    if not isinstance(query, str):
        raise ValueError('Text query required.')
    if not set(categories) <= {'evidenced', 'developing', 'self_reported'}:
        raise ValueError('Unsupported documentation category.')
    skills = {c['skill_id']: c['canonical_name'] for j in report['jobs'] for c in j['concepts']}
    profile_names = [r['canonical_name'] for r in report['profile'] if r['evidence_status'] in categories]
    effective = ' '.join([query.strip()] + profile_names + (report['preferences'].get('role_areas', []) if roles else [])).strip()
    if not effective:
        raise ValueError('Enter a query or select documented concepts/role preferences.')
    eligible = []
    decisions = []
    by = {j['job']['job_id']: j for j in report['jobs']}
    for item in report['jobs']:
        include = True
        reasons = []
        for enabled, pref_field, field in [(locations, 'locations', 'location'), (work_types, 'work_types', 'work_type')]:
            if not enabled:
                continue
            prefs = report['preferences'].get(pref_field, [])
            if not prefs:
                raise ValueError('No saved ' + pref_field + ' preferences.')
            v = item['metadata'].get(field, '')
            accepted = normal(v) in {normal(x) for x in prefs} if normal(v) else unknown
            include = include and accepted
            reasons.append(dict(field=field, value=v, accepted=accepted, unknown=not bool(normal(v))))
        decisions.append(dict(job_id=item['job']['job_id'], included=include, reasons=reasons))
        if include:
            eligible.append(item['job'])
    bm = rank_jobs(eligible, effective, limit=max(1, len(eligible))) if eligible else []
    lex = {r['job_id']: r for r in bm}
    sem = []
    if mode != 'BM25' and eligible:
        if encoder is None:
            raise ValueError('Semantic/Hybrid requires explicit encoder loading; no fallback disguised as semantic.')
        from .semantic_retrieval import rank
        sem=rank(eligible,effective,encoder)
    semantic = {r['job_id']: r for r in sem}
    scores = {}
    if mode == 'Hybrid':
        for ranking in (bm, sem):
            for rank, r in enumerate(ranking, 1):
                scores[r['job_id']] = scores.get(r['job_id'], 0) + 1 / (60 + rank)
        ids = sorted(scores, key=lambda x: (-scores[x], x))
    elif mode == 'Semantic':
        ids = [r['job_id'] for r in sem]
    else:
        ids = [r['job_id'] for r in bm]
    rows = [dict(job_id=i, title=by[i]['job']['title'], bm25=lex.get(i), semantic=semantic.get(i), rrf=scores.get(i), actions=by[i]['actions'], concepts=by[i]['concepts'], languages=by[i]['languages']) for i in ids[:limit]]
    return dict(effective_query=effective, mode=mode, results=rows, filter_decisions=decisions, model=dict(id=MODEL, revision=REVISION) if mode != 'BM25' else None, scope='Filters BEFORE ranking; exact normalised metadata; unknown explicit. Hybrid reciprocal rank fusion k=60, not calibrated relevance. Overlapping token passages; maximum score may favour longer documents. Similarity is not a requirement, qualification, confidence or suitability. Profile expansion explicitly selects documentation categories.')
