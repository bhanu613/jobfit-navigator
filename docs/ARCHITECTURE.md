# Architecture

JobFit Navigator has two parts that work separately: reading requirements and searching listings. A search score never changes how a requirement is labelled.

## Reading requirements

For each saved listing the app does this:

1. Finds concept names and aliases in the text and records exactly where each one appears.
2. Labels each mention as required, desirable, not required or uncertain, using rules that look at the surrounding clause.
3. Combines the labels into one status per concept per listing. If the wording is mixed or unclear, the status is uncertain.
4. Lets you override a label with a saved review and a reason.
5. Compares the result with your profile notes and counts concepts across all saved listings.

The rules cover plain statements such as "Python is required", lists with or without "and", "you must have" wording, repeated statements across a list, "need not" wording, and requirement headings in English and German. Anything outside them stays uncertain, so you can check the original text.

A saved review belongs to the listing text it was made on. If the listing is edited, or the rule changes later, the app flags the review instead of silently reusing it.

## Searching

Search runs in this order:

1. Location and work-type filters remove listings first.
2. The remaining listings are ranked by BM25, by semantic search, or by both.
3. Hybrid search merges the two rankings with reciprocal rank fusion (k = 60).

Semantic search uses `paraphrase-multilingual-MiniLM-L12-v2` at a pinned revision. Listings are split into overlapping passages of tokens, each passage is embedded, and the listing keeps the score of its best passage. The model is used as published and is not trained here.

Semantic and Hybrid need the model to be loaded. If it is not available, the app shows an error and does not switch to BM25 on its own. A search with no text can still browse listings using the filters.

## Storage and launch

Everything is stored in SQLite: listings, profiles, aliases, revisions and reviews. Analysis reads from a temporary copy of the database, so viewing never changes saved data.

The app has two modes:

- **Local:** keeps a persistent workspace on your machine.
- **Demo:** starts a temporary session with fictional data.

`launch.py` loads PyTorch before Streamlit starts. `tools/update_existing.py` backs up the source and database before copying new source files, and it never overwrites the database or the environment.

Code for the search is in `jobfit/jobfit_navigation_engine.py` and `jobfit/semantic_retrieval.py`.
