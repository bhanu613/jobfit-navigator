# Limits, causes and remedies

## Catalogue detection
Literal names and aliases identify concepts; unknown terms are not inferred from general meaning. Remedy: add missing names through Manage concepts and inspect source matches. Different concepts should not share misleading aliases. Future work: curate a labelled vocabulary and measure held-out detection accuracy.

## Bounded interpretation
Regex and complete clause templates recognise explicit patterns, not universal grammar. The demonstrated comma-plus and request forms are covered. Conditional wording, unknown list members, learning requirements and conflicting statements may need review. Arbitrary cue proximity can attach the wrong requirement, so incomplete comma-plus lists stay uncertain. Remedy: inspect source-linked evidence and save a reasoned interpretation. Future work: annotate scope and negative examples before evaluating parsers or classifiers.

## Aggregation and profile
One concept contributes one category per job. Mixed categories request review. Source-bound manual decisions override automatic rules and are retained. Profile and language statements are user-reported, not independently assessed ability. Missing documentation does not prove missing skill.

## Search
BM25 measures lexical relevance. The pretrained multilingual encoder measures semantic relatedness across passages. Hybrid combines ranks, not calibrated hiring probabilities. A negated skill can still rank because relatedness is not logical entailment. Remedy: read original wording and requirement categories. Future work: build held-out relevance judgments and evaluate requirement-aware reranking.

## Evidence and runtime
Regression tests cover specific examples, not corpus-level precision or recall. Windows launch and real semantic search have been checked locally. Fresh installation, cloud execution and cross-platform behaviour require separate verification. The local launcher preloads PyTorch before Streamlit; the underlying cause of environment-specific DLL failures has not been established. Dependencies are specified but not fully transitively locked.
No Transformer training, LLM API, ESCO mapping, authentication or production hiring guarantee is claimed.
