"""Narrow heading/list inheritance; installed confident interpretations always win."""
import re
HEADINGS = {'requirements': 'required', 'required skills': 'required', 'must have': 'required', 'must-have': 'required', 'essential skills': 'required', 'anforderungen': 'required', 'voraussetzungen': 'required', 'erforderliche kenntnisse': 'required', 'nice to have': 'desirable', 'nice-to-have': 'desirable', 'desirable skills': 'desirable', 'preferred skills': 'desirable', 'wünschenswert': 'desirable', 'von vorteil': 'desirable'}

def heading_result(text, mention, mentions, prior):
    if prior[0] != 'uncertain':
        return prior
    left = text.rfind('\n', 0, mention['start']) + 1
    right = text.find('\n', mention['end'])
    right = len(text) if right < 0 else right
    line = text[left:right].rstrip('\r')
    if not re.match('^\\s*(?:[-*•]|\\d+[.)])\\s+', line):
        return prior
    rows = sorted((m for m in mentions if left <= m['start'] and m['end'] <= right), key=lambda m: m['start'])
    if not rows or any((a['end'] > b['start'] for a, b in zip(rows, rows[1:]))):
        return prior
    for m in reversed(rows):
        line = line[:m['start'] - left] + 'SKILL' + line[m['end'] - left:]
    if not re.fullmatch('\\s*(?:[-*•]|\\d+[.)])\\s+SKILL(?:\\s*(?:,\\s*(?:and\\s+|und\\s+)?|and\\s+|und\\s+|&\\s*)SKILL)*\\s*', line, re.I):
        return prior
    for previous in reversed(text[:left].splitlines()[-12:]):
        clean = previous.strip()
        if not clean:
            return prior
        if re.match('^(?:[-*•]|\\d+[.)])\\s+', clean):
            continue
        label = clean.lstrip('#').strip().rstrip(':').strip().casefold()
        return (HEADINGS[label], 'explicit_heading_plain_bullet_v1') if label in HEADINGS else prior
    return prior
