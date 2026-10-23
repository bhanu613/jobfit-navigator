"""Bounded requirement interpretation; not a general grammatical parser."""
import re
REQUIRED = re.compile('\\b(?:required|mandatory|must|essential|needed|erforderlich|voraussetzung|zwingend|notwendig)\\b', re.I)
DESIRABLE = re.compile('\\b(?:desirable|prefer(?:red|ably)|optional|nice[ -]to[ -]have|a\\s+plus|wünschenswert|von\\s+vorteil|idealerweise)\\b', re.I)
COMPLEX = re.compile('\\b(?:not\\s+only|nicht\\s+nur|unless|either|or|oder|except|although|but|aber|jedoch)\\b', re.I)
NEGATED = re.compile('\\b(?:not\\s+(?:(?:strictly|necessarily)\\s+)?(?:required|necessary|essential|mandatory|needed)|nicht\\s+(?:zwingend\\s+)?(?:erforderlich|notwendig)|keine?\\b[^.;\\n]{0,70}\\b(?:erforderlich|notwendig)|no\\b[^.;\\n]{0,70}\\b(?:required|necessary|essential|mandatory|needed))\\b', re.I)
UNRESOLVED_NEGATION = re.compile("\\b(?:not|never|without|no|nicht|nie|ohne|kein\\w*|needn['’]t|don['’]t|doesn['’]t)\\b|\\b(?:need|have)\\s+not\\b", re.I)

def interpret_clause(text, *, shared_scope=False):
    if not isinstance(text, str) or not text.strip():
        raise ValueError('Clause must be nonblank text.')
    if shared_scope:
        return ('uncertain', 'shared_clause_review')
    if COMPLEX.search(text):
        return ('uncertain', 'complex_scope_review')
    negated_spans = list(NEGATED.finditer(text))
    if negated_spans:
        remainder = NEGATED.sub(' ', text)
        if REQUIRED.search(remainder) or DESIRABLE.search(text) or UNRESOLVED_NEGATION.search(remainder):
            return ('uncertain', 'mixed_cues_review')
        return ('not_required', 'explicit_not_required_v2')
    if UNRESOLVED_NEGATION.search(text):
        return ('uncertain', 'unresolved_negation_review')
    required, desirable = (bool(REQUIRED.search(text)), bool(DESIRABLE.search(text)))
    if required and desirable:
        return ('uncertain', 'mixed_cues_review')
    if required:
        return ('required', 'explicit_required_v2')
    if desirable:
        return ('desirable', 'explicit_desirable_v2')
    return ('uncertain', 'no_explicit_status_cue')

def clause_bounds(text, start, end):
    separators = '.!?;\n\r'
    left = max((text.rfind(char, 0, start) for char in separators), default=-1) + 1
    positions = [text.find(char, end) for char in separators]
    right = min((pos for pos in positions if pos != -1), default=len(text))
    return (left, right)

def has_multiple_concepts(mentions, left, right):
    return len({m['skill_id'] for m in mentions if left <= m['start'] and m['end'] <= right}) > 1

def interpret_mention(text, mention, mentions):
    """Interpret one span; accept only narrowly recognised coordinated lists."""
    left, right = clause_bounds(text, mention['start'], mention['end'])
    clause = text[left:right]
    local = sorted((m for m in mentions if left <= m['start'] and m['end'] <= right), key=lambda m: (m['start'], m['end']))
    shared = has_multiple_concepts(local, left, right)
    if not shared:
        status, rule = interpret_clause(clause, shared_scope=False)
        return (status, rule)
    fallback = ('uncertain', 'shared_clause_review')
    prefix = text[left:local[0]['start']].strip()
    if prefix not in ('', '-', '*', '•'):
        return fallback
    if any((a['end'] > b['start'] for a, b in zip(local, local[1:]))):
        return fallback
    gaps = [text[a['end']:b['start']].strip().casefold() for a, b in zip(local, local[1:])]
    allowed = {',', 'and', 'und', ', and', ', und', '&'}
    if not gaps or any((gap not in allowed for gap in gaps)):
        return fallback
    if not any((re.fullmatch(',?\\s*(?:and|und|&)', gap) for gap in gaps)):
        return fallback
    suffix = text[local[-1]['end']:right].strip()
    predicates = (('required', '(?:are|is)\\s+(?:required|mandatory|essential|needed)'), ('desirable', '(?:are|is)\\s+(?:desirable|preferred|optional|(?:a\\s+)?plus|nice[ -]to[ -]have)'), ('not_required', '(?:are|is)\\s+not\\s+(?:required|necessary|mandatory|essential|needed)'), ('required', '(?:sind|ist)\\s+(?:erforderlich|notwendig|zwingend)'), ('desirable', '(?:sind|ist)\\s+(?:wünschenswert|von\\s+Vorteil|optional)'), ('not_required', '(?:sind|ist)\\s+nicht\\s+(?:erforderlich|notwendig)'))
    for status, pattern in predicates:
        if re.fullmatch(pattern, suffix, re.I):
            return (status, 'coordinated_subject_list_v1')
    return fallback
_interpret_mention_before_request_repair = interpret_mention
_LIST = 'SKILL(?:\\s*(?:,\\s*(?:(?:and|und|&)\\s*)?|(?:and|und|&)\\s*)SKILL)*'
_EXPERIENCE = '(?:experience|kenntnisse|erfahrung)'
_REQUIRED_PREDICATE = '(?:(?:is|are)\\s+(?:required|mandatory|essential|needed)|(?:ist|sind)\\s+(?:erforderlich|notwendig|zwingend))'
_LEARNING_SCOPE = re.compile('\\b(?:learn(?:ing)?|willing(?:ness)?|train(?:ing)?|lernen|lernbereitschaft|bereitschaft)\\b', re.I)
_REQUEST_PATTERNS = ('(?:i|we)\\s+(?:also\\s+)?(?:need|require)\\s+(?:experience\\s+(?:with|in)\\s+)?' + _LIST, '(?:i|we)\\s+(?:also\\s+)?(?:need|require)\\s+(?:(?:a|an)\\s+)?(?:freelancer|developer|candidate|someone|person)\\s+with\\s+' + _LIST + '\\s+experience', '(?:i|we)\\s+(?:also\\s+)?(?:need|require)\\s+' + _LIST + '\\s+experienced\\s+(?:guy|person|candidate|developer)', 'experience\\s+(?:with|in)\\s+' + _LIST + '\\s+' + _REQUIRED_PREDICATE, '(?:erfahrung|kenntnisse)\\s+(?:mit|in)\\s+' + _LIST + '\\s+' + _REQUIRED_PREDICATE)

def interpret_mention(text, mention, mentions):
    """Recognise complete bounded request patterns, never arbitrary cue proximity."""
    left, right = clause_bounds(text, mention['start'], mention['end'])
    clause = text[left:right]
    if _LEARNING_SCOPE.search(clause):
        return ('uncertain', 'learning_scope_review_v1')
    local = sorted((m for m in mentions if left <= m['start'] and m['end'] <= right), key=lambda m: (m['start'], m['end']))
    if local and (not any((a['end'] > b['start'] for a, b in zip(local, local[1:])))):
        cursor = left
        parts = []
        for item in local:
            parts.extend((text[cursor:item['start']], 'SKILL'))
            cursor = item['end']
        parts.append(text[cursor:right])
        template = ' '.join(''.join(parts).split()).strip()
        template = re.sub('^[-*•]\\s*', '', template)
        if any((re.fullmatch(pattern, template, re.I) for pattern in _REQUEST_PATTERNS)):
            return ('required', 'explicit_request_scope_v1')
    if re.search('\\b(?:need|require|requires)\\b', clause, re.I):
        return ('uncertain', 'request_scope_review_v1')
    return _interpret_mention_before_request_repair(text, mention, mentions)
_completion_previous_interpret_mention = interpret_mention

def interpret_mention(text, mention, mentions):
    from .completion_heading import heading_result
    return heading_result(text, mention, mentions, _completion_previous_interpret_mention(text, mention, mentions))

# A whole-clause prefix rule: not an arbitrary plus-proximity heuristic.
_before_plus_prefix = interpret_mention

def interpret_mention(text, mention, mentions):
    left, right = clause_bounds(text, mention['start'], mention['end'])
    local = sorted((m for m in mentions if left <= m['start'] and m['end'] <= right), key=lambda m: m['start'])
    if local and not any(a['end'] > b['start'] for a,b in zip(local,local[1:])):
        cursor = left
        pieces = []
        for m in local:
            pieces.extend((text[cursor:m['start']], 'SKILL'))
            cursor = m['end']
        pieces.append(text[cursor:right])
        template = ' '.join(''.join(pieces).split())
        if re.fullmatch(r'(?:[-*•]\s*)?plus(?:\s*:\s*|\s+)SKILL(?:\s*(?:,\s*(?:(?:and|und)\s+)?|(?:and|und|&)\s+)SKILL)*', template, re.I):
            return ('desirable', 'explicit_plus_prefix_v1')
    return _before_plus_prefix(text, mention, mentions)


_before_final_refinement = interpret_mention
_FINAL_LIST = r'SKILL(?:\s*(?:,\s*(?:(?:and|und|&)\s+)?|(?:and|und|&)\s+)SKILL)*'
_FINAL_PATTERNS = (
 ('desirable', _FINAL_LIST+r'\s+(?:are|is)\s+(?:a\s+plus|desirable|preferred|optional)'),
 ('required', _FINAL_LIST+r'\s+(?:knowledge|experience)\s+(?:is|are)\s+(?:needed|required|essential)'),
 ('required', r'(?:i|we)\s+(?:need|require)\s+(?:(?:a|an)\s+)?(?:guy|person|candidate|developer|someone)\s+experienced\s+in\s+'+_FINAL_LIST),
 ('required', r'(?:strictly\s+)?(?:need|require)\s+(?:someone|a\s+person|a\s+candidate)\s+with\s+experience\s+(?:in|with)\s+'+_FINAL_LIST),
)

def interpret_mention(text, mention, mentions):
    left,right=clause_bounds(text,mention['start'],mention['end'])
    local=sorted((m for m in mentions if left<=m['start'] and m['end']<=right),key=lambda m:(m['start'],m['end']))
    if local and not any(a['end']>b['start'] for a,b in zip(local,local[1:])):
        cursor=left;parts=[]
        for m in local:
            parts.extend((text[cursor:m['start']],'SKILL'));cursor=m['end']
        parts.append(text[cursor:right]);template=' '.join(''.join(parts).split());template=re.sub(r'^[-*•]\s*','',template)
        if not _LEARNING_SCOPE.search(template):
            for status,pattern in _FINAL_PATTERNS:
                if re.fullmatch(pattern,template,re.I):return status,'bounded_final_list_v1'
        if ',' in template and re.search(r'\b(?:are|is)\s+a\s+plus\s*$',template,re.I):
            return 'uncertain','incomplete_final_list_review'
    return _before_final_refinement(text,mention,mentions)
