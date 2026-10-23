"""Read-only lexical search and descriptive corpus counts. No schema changes."""
import math
import re
import sqlite3
from collections import Counter
from pathlib import Path
VERSION = 'lexical-search-0.1'

def tokens(text):
    return re.findall('[^\\W_]+(?:[+#]+)?', text.casefold(), re.UNICODE)

def read_jobs(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError(f'Database not found: {path}')
    connection = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    try:
        cursor = connection.execute('SELECT job_id,title,description_text FROM jobs ORDER BY job_id')
        return [dict(zip(('job_id', 'title', 'description_text'), row)) for row in cursor]
    finally:
        connection.close()

def rank_jobs(jobs, query, *, limit=20):
    if not isinstance(query, str) or not query.strip():
        raise ValueError('Enter a nonblank query.')
    if type(limit) is not int or limit <= 0:
        raise ValueError('limit must be a positive integer.')
    terms = list(dict.fromkeys(tokens(query)))
    if not terms:
        raise ValueError('Query must contain searchable letters or digits.')
    if not jobs:
        return []
    documents = [Counter(tokens(job['title'] + '\n' + job['description_text'])) for job in jobs]
    lengths = [sum(doc.values()) for doc in documents]
    average = sum(lengths) / len(lengths) or 1
    df = {term: sum((term in doc for doc in documents)) for term in terms}
    rows = []
    for job, counts, length in zip(jobs, documents, lengths):
        signals = []
        for term in terms:
            tf = counts[term]
            if not tf:
                continue
            idf = math.log(1 + (len(jobs) - df[term] + 0.5) / (df[term] + 0.5))
            contribution = idf * tf * 2.5 / (tf + 1.5 * (0.25 + 0.75 * length / average))
            signals.append({'term': term, 'occurrences': tf, 'jobs_containing_term': df[term], 'score_contribution': contribution})
        if signals:
            rows.append({'job_id': job['job_id'], 'title': job['title'], 'lexical_score': sum((s['score_contribution'] for s in signals)), 'matched_terms': [s['term'] for s in signals], 'signals': signals})
    rows.sort(key=lambda row: (-row['lexical_score'], row['job_id']))
    return rows[:limit]

def search_jobs(path, query, *, limit=20):
    return rank_jobs(read_jobs(path), query, limit=limit)

def mention_frequencies(path):
    from .skill_mentions import find_skill_mentions
    jobs = read_jobs(path)
    counts, names = (Counter(), {})
    for job in jobs:
        seen = set()
        for mention in find_skill_mentions(job['description_text'], database_path=path):
            key = mention['skill_key']
            names[key] = mention['canonical_name']
            seen.add(key)
        counts.update(seen)
    return {'saved_job_count': len(jobs), 'scope': 'Catalogue mentions, NOT required-skill counts. Negated, desirable and ambiguous mentions are included. Technical reviews are not applied.', 'skills': [{'skill_key': key, 'canonical_name': names[key], 'jobs_with_mention': count, 'saved_jobs_percent': round(100 * count / len(jobs), 1)} for key, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]}

def render_search_and_insights(path):
    import streamlit as st
    st.divider()
    st.header('Search saved jobs and inspect coverage')
    st.caption('Lexical baseline: title and description tokens have equal weight. No embeddings, translation, synonym expansion or candidate suitability scoring.')
    search_tab, corpus_tab = st.tabs(['Search saved text', 'Catalogue mention counts'])
    with search_tab:
        with st.form('navigator_lexical_search_v01'):
            query = st.text_input('Search query', placeholder='Python NLP working student')
            submitted = st.form_submit_button('Search saved jobs')
        if submitted:
            try:
                results = search_jobs(path, query)
                st.caption('BM25 text-relevance score, not a percentage or qualification judgement. One or more query terms must match. Required/not-required wording is not interpreted in ranking.')
                if not results:
                    st.info('No lexical matches. This does not establish that no relevant opportunities exist.')
                for row in results:
                    with st.expander(f"Job {row['job_id']}: {row['title']} | lexical score {row['lexical_score']:.3f}"):
                        st.write('Matched terms:', ', '.join(row['matched_terms']))
                        st.dataframe(row['signals'], hide_index=True)
                        st.caption('Use the existing Analysis tab for source evidence, profile records and saved reviews.')
            except (ValueError, sqlite3.Error, OSError) as error:
                st.error(f'Search failed: {error}')
    with corpus_tab:
        st.warning('Counts describe only your saved collection and approved aliases. They are not labour-market statistics or required-skill frequencies.')
        if st.button('Calculate current mention counts', key='navigator_corpus_mentions_v01'):
            try:
                result = mention_frequencies(path)
                st.write('Saved jobs:', result['saved_job_count'])
                st.caption(result['scope'])
                if result['skills']:
                    st.dataframe(result['skills'], hide_index=True)
                else:
                    st.info('No approved mentions found, or no saved jobs.')
            except (ValueError, sqlite3.Error, OSError) as error:
                st.error(f'Corpus count failed: {error}')
