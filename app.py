from pathlib import Path
import os,json,logging
import streamlit as st
from jobfit import navigator_service as svc,job_store as store,navigator_extensions as ext,navigator_broader as broad,jobfit_navigation_engine as nav,workspace as ws,language_reviews as lr,completion_services as completion
from jobfit.concept_management import add_concept
from jobfit.text_processing import alias_spans
from jobfit.release_features import search_listings
st.set_page_config(page_title='JobFit Navigator',layout='wide')
MODE=os.environ.get('JOBFIT_MODE','demo').lower()
if MODE not in ('demo','local'):st.error('Invalid JOBFIT_MODE');st.stop()
try:
 if MODE=='demo':
  if 'workspace' not in st.session_state:st.session_state.workspace=ws.public_demo()
  handle,DB=st.session_state.workspace
 else:
  DB=Path(os.environ.get('JOBFIT_DB',str(Path(__file__).parent/'data/navigator_local.db'))).resolve()
  if not DB.is_file():st.error('Local database missing. Run Start-Local.ps1 to select a safe copy.');st.stop()
  if st.session_state.get('setup_path')!=str(DB):ws.setup(DB);st.session_state.setup_path=str(DB)
except Exception as e:st.error('Workspace setup failed: '+str(e));st.stop()
LABEL={'required':'Required','desirable':'Desirable','not_required':'Not required','uncertain':'Needs review','evidenced':'Evidence recorded','developing':'Developing','self_reported':'Self-reported','not_documented':'Not recorded'}
def label(x):return LABEL.get(x,x)
def perform(fn):
 try:fn()
 except Exception as e:st.error(str(e));return
 st.rerun()
# Durable navigation must not use a widget-owned key: an early rerun during
# profile creation skips rendering and Streamlit cleans up omitted widget keys.
if 'page' not in st.session_state:
 st.session_state.page=st.session_state.get('navigation_page','Overview')
people=svc.list_candidates(database_path=DB)
with st.sidebar:
 st.header('Your workspace');st.caption('Session workspace' if MODE=='demo' else 'Local workspace')
 with st.expander('Create a profile'):
  with st.form('create_profile'):
   name=st.text_input('Display name',max_chars=100);create=st.form_submit_button('Create profile')
  if create:
   def create_person():ws.text(name,100);store.create_candidate(name,database_path=DB)
   perform(create_person)
 if not people:st.info('Create a profile to begin.');st.stop()
 cid=st.selectbox('Active profile',[p['candidate_id'] for p in people],format_func=lambda i:next(p['display_name'] or str(i) for p in people if p['candidate_id']==i),key='active_profile')
 page=st.radio('Go to',['Overview','Job library','Find opportunities','Compare a job','Collection insights','Profile','Manage concepts','About'],key='page')
 st.session_state.navigation_page=page
 if MODE=='demo' and st.button('Reset demo workspace'):st.session_state.clear();st.rerun()
contexts=st.session_state.setdefault('contexts',{});state=contexts.setdefault(str(DB)+'::'+str(cid),{})
def goto(page,jid=None):
 st.session_state.page=page
 st.session_state.navigation_page=page
 if jid is not None:state['comparison']=jid
sig=ws.signature(DB)
if state.get('signature')!=sig:
 if state.pop('results',None) is not None:state['stale']=True
 state['signature']=sig
jobs=svc.list_jobs(database_path=DB)
st.title('JobFit Navigator')
def metadata_view(meta):
 cols=st.columns(3)
 for col,key in zip(cols,('company','location','work_type')):
  col.caption(key.replace('_',' ').title())
  col.write(meta.get(key) or 'Not recorded')
 if meta.get('source_language'):st.caption('Listing language: '+meta['source_language'])

report=None
if page in ('Overview','Find opportunities','Compare a job','Collection insights'):
 try:report=nav.candidate_report(DB,cid)
 except Exception as e:
  logging.exception('Analysis failed');st.warning('Analysis unavailable. Source records remain accessible in Job library.')
  with st.expander('Technical details'):st.text(str(e))
  if page!='Overview':st.stop()
def listing_form(prefix,job=None):
 job=job or {};metadata=broad.get_metadata(DB,job['job_id']) if job else {}
 with st.form(prefix):
  v={}
  v['title']=st.text_input('Role title',value=job.get('title',''),max_chars=250)
  v['description_text']=st.text_area('Listing text',value=job.get('description_text',''),height=200,max_chars=100000)
  v['source_description']=st.text_input('Source description',value=job.get('source_description',''),max_chars=1000)
  v['source_url']=st.text_input('Source URL (optional)',value=job.get('source_url') or '',max_chars=2048)
  meta={k:st.text_input(k.replace('_',' ').title(),value=metadata.get(k,''),max_chars=1000) for k in broad.METADATA_FIELDS}
  if job:st.caption('A revision is retained. Old reviews do not apply to changed source.')
  save=st.form_submit_button('Save changes' if job else 'Save listing')
 if save:perform(lambda:ws.save_listing(DB,job.get('job_id'),v,meta,ws.fingerprint(job) if job else None))
if page=='Overview':
 a,b=st.columns(2);a.metric('Saved opportunities',len(jobs));b.metric('Profile statements',len(store.read_candidate_skills(cid,database_path=DB)))
 st.subheader('Your collection')
 st.button('Browse opportunities',on_click=goto,args=('Find opportunities',))
 st.subheader('Required concepts to document')
 if report:st.dataframe([{'Concept':x['concept'],'Required in jobs':len(x['required_jobs']),'Your documentation':label(x['profile_status'])} for x in report['priorities'] if x['required_jobs'] and x['profile_status']!='evidenced'],hide_index=True,width='stretch')
elif page=='Job library':
 with st.expander('Save a listing',expanded=not jobs):listing_form('new_listing')
 st.dataframe([{'ID':j['job_id'],'Title':j['title'],'Saved':j['date_added'],'Status':j['application_status'],'Company':broad.get_metadata(DB,j['job_id']).get('company') or 'Not recorded','Location':broad.get_metadata(DB,j['job_id']).get('location') or 'Not recorded','Work type':broad.get_metadata(DB,j['job_id']).get('work_type') or 'Not recorded','Source':j['source_description']} for j in jobs],hide_index=True,width='stretch')
 if jobs:
  jid=st.selectbox('Select saved listing',[j['job_id'] for j in jobs],format_func=lambda i:next(f"{j['title']} (ID {i})" for j in jobs if j['job_id']==i))
  job=next(j for j in jobs if j['job_id']==jid);st.subheader(job['title']);metadata_view(broad.get_metadata(DB,jid));st.text(job['description_text']);st.write('Source:',job['source_description']);st.write('URL:',job.get('source_url') or 'Not recorded')
  st.button('Open comparison',on_click=goto,args=('Compare a job',jid))
  with st.expander('Edit complete listing'):listing_form('edit_'+str(jid),job)
  status=st.selectbox('Application status',ext.APPLICATION_STATUSES,index=ext.APPLICATION_STATUSES.index(job['application_status']) if job['application_status'] in ext.APPLICATION_STATUSES else 0)
  if st.button('Update application status'):perform(lambda:ext.update_application_status(DB,jid,status))
  with st.expander('Delete listing'):
   confirm=st.checkbox('Permanently delete listing and linked reviews')
   if st.button('Delete listing',disabled=not confirm):perform(lambda:ext.delete_job(DB,jid))
 st.download_button('Download metadata CSV',completion.csv_bytes([dict({k:j.get(k) for k in ('job_id','title','date_added','application_status','source_description','source_url')},**broad.get_metadata(DB,j['job_id'])) for j in jobs]),'jobfit-metadata.csv','text/csv')
 with st.expander('Workspace backup'):
  if st.button('Prepare backup'):state['backup']=ws.backup_bytes(DB)
  if state.get('backup'):st.download_button('Download backup',state['backup'],'jobfit-private.db')
elif page=='Profile':
 skills=svc.list_skills(database_path=DB);current=store.read_candidate_skills(cid,database_path=DB)
 st.subheader('Skills and evidence');st.dataframe(current,hide_index=True,width='stretch')
 with st.form('skill_statement_'+str(cid)):
  sid=st.selectbox('Skill',[s['skill_id'] for s in skills],format_func=lambda i:next(s['canonical_name'] for s in skills if s['skill_id']==i))
  status=st.selectbox('Documentation status',['evidenced','developing','self_reported'],format_func=label);note=st.text_area('Evidence or learning note',max_chars=5000);save=st.form_submit_button('Save skill statement')
 if save:perform(lambda:store.save_candidate_skill(cid,sid,status,note or None,database_path=DB))
 if current:
  remove=st.selectbox('Skill statement to remove',[r['skill_id'] for r in current],format_func=lambda i:next(r['canonical_name'] for r in current if r['skill_id']==i))
  if st.button('Remove skill statement'):perform(lambda:svc.remove_candidate_skill(cid,remove,database_path=DB))
 prefs=broad.get_preferences(DB,cid)
 with st.form('preferences_'+str(cid)):
  st.caption('Preferences: one value per line; commas inside values are preserved.')
  values={k:[x.strip() for x in st.text_area(k.replace('_',' ').title(),value='\n'.join(prefs[k]),max_chars=3000).splitlines() if x.strip()] for k in broad.PREFERENCE_FIELDS};save=st.form_submit_button('Save preferences')
 if save:perform(lambda:broad.save_preferences(DB,cid,values))
 langs=ext.list_languages(DB,cid);st.subheader('Language statements');st.dataframe(langs,hide_index=True,width='stretch')
 with st.form('languages_'+str(cid)):
  language=st.selectbox('Language',ext.LANGUAGES);level=st.selectbox('Reported level',ext.LEVELS);note=st.text_input('Language note',max_chars=2000);save=st.form_submit_button('Save language')
 if save:perform(lambda:ext.save_language(DB,cid,language,level,note))
 if langs:
  remove=st.selectbox('Language to remove',[x['language'] for x in langs])
  if st.button('Remove language'):perform(lambda:ext.remove_language(DB,cid,remove))
 st.download_button('Download profile JSON',json.dumps(dict(profile=current,languages=langs,preferences=prefs),ensure_ascii=False,indent=2),'jobfit-profile.json')
elif page=='Find opportunities':
 st.subheader('Find saved opportunities')
 if state.pop('stale',False):st.info('Library changed. Search again to refresh results.')
 settings=state.setdefault('search',{});prefix='search_'+str(cid)+'_'
 def field(kind,title,name,default,**kwargs):
  key=prefix+name
  if key not in st.session_state:st.session_state[key]=settings.get(name,default)
  value=getattr(st,kind)(title,key=key,**kwargs);settings[name]=value;return value
 query=field('text_input','What are you looking for?','query','',max_chars=2000)
 available_locations=sorted({x['metadata'].get('location','') for x in report['jobs']}-{''})
 available_types=sorted({x['metadata'].get('work_type','') for x in report['jobs']}-{''})
 for name,available in [('locations_direct',available_locations),('types_direct',available_types)]:
  key=prefix+name
  if key in st.session_state:st.session_state[key]=[v for v in st.session_state[key] if v in available]
  if name in settings:settings[name]=[v for v in settings[name] if v in available]
 selected_locations=field('multiselect','Location','locations_direct',[],options=available_locations)
 selected_types=field('multiselect','Work type','types_direct',[],options=available_types)
 unknown=field('checkbox','Include listings with missing selected metadata','unknown',False)
 with st.expander('Search options'):
  mode=field('selectbox','Search method','mode','BM25',options=['BM25','Semantic','Hybrid'])
  categories=field('multiselect','Include profile concepts','categories',[],options=['evidenced','developing','self_reported'],format_func=label)
  roles=field('checkbox','Include saved role interests','roles',False)
  st.caption('Semantic search downloads its model on first use.')
 if st.button('Search saved jobs',type='primary'):
  state.pop('results',None)
  try:
   encoder=None
   if mode!='BM25' and (query.strip() or categories or roles):
    @st.cache_resource
    def encoder_resource():return nav.load_encoder()
    with st.spinner('Loading search model...'):encoder=encoder_resource()
   state['results']=search_listings(report,query,selected_locations=selected_locations,selected_work_types=selected_types,include_unknown=unknown,categories=categories,roles=roles,mode=mode,encoder=encoder)
   state['submitted']=dict(settings)
  except Exception as e:
   st.error('Search could not finish. BM25 keyword search remains available.')
   with st.expander('Error details'):st.text(str(e))
 result=state.get('results')
 if result is not None:
  st.caption(str(len(result['results']))+' results | '+result.get('method','BM25')+(' | '+result['effective_query'] if result['effective_query'] else ''))
  if settings!=state.get('submitted'):st.info('Settings changed. Search again to update results.')
  if not result['results']:st.info('No matching saved listings.')
  for row in result['results']:
   with st.container(border=True):
    st.subheader(row['title']);st.caption('Listing ID '+str(row['job_id']));metadata_view(row['metadata'])
    description=row['description_text'];st.text(description[:450]+('...' if len(description)>450 else ''))
    with st.expander('Full description'):
     st.text(description);st.write('Source:',row['source_description']);st.write('URL:',row.get('source_url') or 'Not recorded')
    if row.get('bm25') or row.get('semantic'):
     with st.expander('Why this result appeared'):
      if row.get('bm25'):st.write('Matched words: '+', '.join(row['bm25']['matched_terms']))
      if row.get('semantic'):st.text(row['semantic']['passage']['text'])
    st.button('Open comparison',key='open_'+str(row['job_id']),on_click=goto,args=('Compare a job',row['job_id']))
elif page=='Compare a job':
 if not report['jobs']:st.info('Save a listing in Job library first.')
 else:
  ids=[j['job']['job_id'] for j in report['jobs']];old=state.get('comparison')
  if old is not None and old not in ids:st.info('Previously selected listing is unavailable. Selecting another listing.')
  if old not in ids:state['comparison']=ids[0]
  key='compare_widget_'+str(cid);st.session_state[key]=state['comparison']
  def remember_comparison():state['comparison']=st.session_state[key]
  jid=st.selectbox('Choose saved listing',ids,format_func=lambda i:next(f"{j['job']['title']} (ID {i})" for j in report['jobs'] if j['job']['job_id']==i),key=key,on_change=remember_comparison)
  listing=next(j for j in report['jobs'] if j['job']['job_id']==jid);job=listing['job'];metadata_view(listing['metadata'])
  st.dataframe([{'Concept':c['canonical_name'],'Requirement':label(c['effective_status']),'Your documentation':label(c['profile_status'])} for c in listing['concepts']],hide_index=True,width='stretch')
  if not listing['concepts']:st.info('No concepts detected. Add missing names or aliases in Manage concepts.')
  for c in listing['concepts']:
   with st.expander(c['canonical_name']+': '+label(c['effective_status'])):
    if c.get('mixed_wording'):st.warning('Mixed mention categories. Review their scope.')
    if c.get('profile_note'):st.write('Your statement:',c['profile_note'])
    for m in c['evidence']:
     st.text(m.get('evidence_text') or job['description_text'][m['start']:m['end']]);st.caption('Automatic: '+label(m['automatic_status'])+'. Effective: '+label(m['effective_status']))
     if m.get('review_rule_changed'):st.warning('Automatic interpretation changed since review. Recheck it.')
     mk=f"{jid}_{m['skill_id']}_{m['start']}"
     with st.form('review_'+mk):
      interpretation=st.selectbox('Interpretation',nav.STATES,index=nav.STATES.index(m['effective_status']),format_func=label);reason=st.text_input('Reason',max_chars=2000);save=st.form_submit_button('Save interpretation')
     if save:perform(lambda:ext.save_review(DB,jid,job['description_text'],dict(m,requirement_status=m['automatic_status']),interpretation,reason))
     if m.get('review') and st.button('Remove interpretation',key='remove_'+mk):perform(lambda:ext.remove_review(DB,jid,job['description_text'],m))
  if listing['languages']:st.subheader('Language wording')
  for l in listing['languages']:
   with st.expander(l['language']+': '+label(l['effective_status'])):
    st.text(l['context_text']);st.write('CEFR candidate:',l.get('cefr_candidate') or 'Not assigned');st.write('Your reported level:',label(l['profile_level']));st.write('Your note:',l.get('profile_note') or 'Not recorded')
    for n in l.get('review_notes',[]):st.caption(n)
    if l.get('review_conflict'):st.warning('Legacy review stores disagree. Resolve explicitly.')
    if l.get('review_drift'):st.warning('Automatic language interpretation changed since review.')
    if l.get('review_sources'):st.caption('Saved interpretation available')
    lk=f"{jid}_{l['language']}_{l['start']}"
    with st.form('language_review_'+lk):
     interpretation=st.selectbox('Language requirement interpretation',nav.STATES,index=nav.STATES.index(l['effective_status']),format_func=label);reason=st.text_input('Language rationale',max_chars=2000);save=st.form_submit_button('Save language interpretation')
    if save:perform(lambda:lr.save(DB,jid,job['description_text'],l['language'],l['start'],l['end'],interpretation,reason))
    if any(r['ledger']=='navigator_language_reviews_v4' for r in l.get('review_sources',[])) and st.button('Remove explicit language interpretation',key='lr_remove_'+lk):perform(lambda:lr.remove(DB,jid,job['description_text'],l['language'],l['start'],l['end']))
  with st.expander('Original listing and source',expanded=True):st.text(job['description_text']);st.write('Source:',job['source_description']);st.write('URL:',job.get('source_url') or 'Not recorded')
  st.download_button('Download comparison JSON',json.dumps(listing,ensure_ascii=False,indent=2),'jobfit-comparison.json')
elif page=='Collection insights':
 st.subheader('Requirements across saved jobs');st.caption('One category per concept per listing.')
 st.dataframe([{'Concept':x['concept'],'Your documentation':label(x['profile_status']),'Required':len(x['required_jobs']),'Desirable':len(x['desirable_jobs']),'Needs review':len(x['review_jobs']),'Not required':len(x.get('not_required_jobs',[])),'Next step':x['next_action']} for x in report['priorities']],hide_index=True,width='stretch')
 if report['priorities']:
  sid=st.selectbox('Trace a concept',[x['skill_id'] for x in report['priorities']],format_func=lambda i:next(x['concept'] for x in report['priorities'] if x['skill_id']==i))
  for listing in report['jobs']:
   for c in listing['concepts']:
    if c['skill_id']==sid:
     with st.expander(f"{listing['job']['title']} (ID {listing['job']['job_id']}): {label(c['effective_status'])}"):
      for m in c['evidence']:st.text(m.get('evidence_text') or m['matched_text']);st.caption(label(m['effective_status']))
 st.subheader('Language requirements');st.dataframe([{'Language':x['language'],'Required':len(x['required_jobs']),'Desirable':len(x['desirable_jobs']),'Needs review':len(x['review_jobs']),'Not required':len(x.get('not_required_jobs',[]))} for x in report['language_priorities']],hide_index=True,width='stretch')
elif page=='Manage concepts':
 st.subheader('Manage concepts');st.caption('Add names and aliases used in your listings.')
 name=st.text_input('New concept name',max_chars=200);raw=st.text_area('Additional aliases, one per line',max_chars=6000);aliases=[x.strip() for x in raw.splitlines() if x.strip()]
 if st.button('Preview literal matches'):
  rows=[]
  for job in jobs:
   hits=sorted({span for term in [name]+aliases if term.strip() for span in alias_spans(job['description_text'],term)})
   if hits:rows.append({'ID':job['job_id'],'Title':job['title'],'Literal spans':len(hits),'Examples':' | '.join(job['description_text'][max(0,a-40):min(len(job['description_text']),b+70)] for a,b in hits[:3])})
  st.dataframe(rows,hide_index=True,width='stretch');st.caption('Literal candidates only; overlap and context interpretation follow.')
 confirm=st.checkbox('I checked the name and aliases for ambiguity')
 if st.button('Add concept',disabled=not confirm):perform(lambda:add_concept(DB,name,aliases))
 st.dataframe(svc.list_skills(database_path=DB),hide_index=True,width='stretch')
 with st.expander('Add or retire an alias for an existing concept'):
  skills=svc.list_skills(database_path=DB);sid=st.selectbox('Existing concept',[x['skill_id'] for x in skills],format_func=lambda i:next(x['canonical_name'] for x in skills if x['skill_id']==i))
  alias=st.text_input('Alias',max_chars=200);active=st.checkbox('Alias active',value=True);reason=st.text_input('Alias-change reason',max_chars=2000)
  if st.button('Save alias change'):perform(lambda:completion.change_alias(DB,sid,alias,active,reason))
  with st.expander('Catalogue history'):st.write(completion.vocabulary(DB))
else:
 st.subheader('About JobFit Navigator')
 st.write('Save listings, compare their requirements with your profile notes, and explore patterns across your collection.')
 st.write('Search with keywords, semantic passages, or hybrid retrieval. Inspect requirement wording against its original source.')
 st.caption('Setup, methods and validation details are included in the project documentation.')
