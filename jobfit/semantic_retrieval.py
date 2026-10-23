import numpy as np
def rank(jobs,query,encoder):
 tokenizer=getattr(encoder,'tokenizer',None)
 if tokenizer is None:raise ValueError('Tokenizer with offset support required.')
 limit=int(encoder.max_seq_length);budget=limit-int(tokenizer.num_special_tokens_to_add(pair=False))
 if budget<8:raise ValueError('Unsupported model input size.')
 if len(tokenizer(query,add_special_tokens=True,truncation=False)['input_ids'])>limit:raise ValueError('Shorten query. Model query truncation is not allowed.')
 chunks=[]
 for job in jobs:
  for field in ('title','description_text'):
   text=job[field];offsets=[(a,b) for a,b in tokenizer(text,add_special_tokens=False,truncation=False,return_offsets_mapping=True)['offset_mapping'] if b>a]
   for i in range(0,len(offsets),max(1,budget*3//4)):
    group=offsets[i:i+budget];a,b=group[0][0],group[-1][1];chunks.append(dict(job_id=job['job_id'],field=field,start=a,end=b,text=text[a:b]))
    if i+budget>=len(offsets):break
 if not chunks:return []
 v=np.asarray(encoder.encode([c['text'] for c in chunks],normalize_embeddings=True,show_progress_bar=False),dtype=float)
 q=np.asarray(encoder.encode([query],normalize_embeddings=True,show_progress_bar=False),dtype=float)[0]
 if v.ndim!=2 or q.ndim!=1 or v.shape!=(len(chunks),len(q)):raise ValueError('Unexpected embedding shape.')
 if not np.isfinite(v).all() or not np.isfinite(q).all():raise ValueError('Nonfinite model output.')
 den=np.linalg.norm(v,axis=1)*np.linalg.norm(q);scores=np.divide(v@q,den,out=np.zeros(len(v)),where=den>0);best={}
 for c,score in zip(chunks,scores):
  jid=c['job_id']
  if jid not in best or score>best[jid]['semantic_score']:best[jid]=dict(job_id=jid,semantic_score=float(score),passage=c)
 return sorted(best.values(),key=lambda x:(-x['semantic_score'],x['job_id']))
