import unicodedata,re
def normalise(text):
 chars=[];spans=[]
 for m in re.finditer(r'.[\u0300-\u036f]*',text,re.S):
  for c in unicodedata.normalize('NFKC',m.group()).casefold():chars.append(' ' if c.isspace() else c);spans.append(m.span())
 return ''.join(chars),spans
def alias_spans(text,alias):
 value,spans=normalise(text);a,_=normalise(alias);pattern=r'\s+'.join(re.escape(x) for x in a.split())
 return [(spans[m.start()][0],spans[m.end()-1][1]) for m in re.finditer(r'(?<!\w)'+pattern+r'(?!\w)',value)] if pattern else []
