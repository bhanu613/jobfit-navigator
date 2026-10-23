# Architecture

## Requirement path
Saved original text -> literal alias spans -> bounded interpretation rules -> optional source-bound review -> one concept category per job -> profile comparison and collection counts.
Detection, interpretation and profile evidence are distinct. Retrieval scores never decide whether a requirement is mandatory.

## Search path
Metadata filters -> eligible listings -> BM25 and/or overlapping semantic passages -> pretrained multilingual encoder -> cosine similarity -> best passage per listing. Hybrid combines lexical and semantic ranks through reciprocal-rank fusion with k=60. Blank-query browsing is unranked.
The implementation and pinned model revision are in jobfit/jobfit_navigation_engine.py and semantic_retrieval.py. Model integration is not model training.

## Storage and launch
SQLite stores jobs, profiles, aliases, revisions and review ledgers. Persistent local mode uses the active workspace; default demo mode creates a temporary fictional session. Profile selection is not authentication.
The updater backs up managed source and the standard database, then copies source without replacing database or environment. The local wrapper loads torch before starting Streamlit. First setup is separate from routine launch.
