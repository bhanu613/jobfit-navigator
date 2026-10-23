"""Metadata-filtered retrieval; browse is intentionally unranked."""
from . import jobfit_navigation_engine as nav

def search_listings(report, query, *, selected_locations=(), selected_work_types=(), include_unknown=False, **options):
    filtered = dict(report)
    filtered['jobs'] = []
    for item in report['jobs']:
        keep = True
        for field, selected in [('location', selected_locations), ('work_type', selected_work_types)]:
            if selected:
                value = nav.normal(item.get('metadata', {}).get(field, ''))
                keep = keep and ((value in {nav.normal(s) for s in selected}) if value else include_unknown)
        if keep:
            filtered['jobs'].append(item)
    if not query.strip() and not options.get('categories') and not options.get('roles'):
        result = dict(effective_query='', method='Browse', results=[dict(job_id=x['job']['job_id'], title=x['job']['title'], bm25=None, semantic=None) for x in filtered['jobs']])
    else:
        result = nav.search(filtered, query, **options)
        result['method'] = options.get('mode','BM25')
    by = {x['job']['job_id']: x for x in filtered['jobs']}
    for row in result['results']:
        item = by[row['job_id']]
        row.update(metadata=dict(item.get('metadata', {})), description_text=item['job']['description_text'], source_description=item['job']['source_description'], source_url=item['job'].get('source_url'))
    return result
