# Limitations

What the app does not do, and what to do about it.

## Concept detection

Concepts are found by their names and aliases. A skill that is not in the list is not detected, and similar words are not matched by meaning.

- If something is missing, add it under **Manage concepts** and preview the matches.
- Avoid aliases that could mean two things.
- Not done: a labelled vocabulary and a measured detection accuracy.

## Requirement wording

The rules cover common patterns, not all grammar. Conditions, lists with unknown members, "willing to learn" wording and statements that contradict each other can be labelled uncertain or wrongly.

- Open the comparison page, read the source text and save your own label with a reason.
- Not done: an annotated set of examples to measure the rules.
- Lists without "and", such as `Python, SQL are required`, are now read. Lists with "not", "or" or "but" still need your own label.

## Profile

Profile and language entries are what you write about yourself. The app does not test them, and a missing entry does not mean a missing skill.

## Search

BM25 matches words. Semantic search matches related meaning, so a listing that says a skill is not needed can still rank high. Hybrid mixes the two rankings and is not a probability of a good fit.

- Read the original wording and the requirement labels before relying on a result.
- Not done: relevance judgments to measure ranking quality, and re-ranking by requirement labels.

## Testing and setup

The 64 tests check specific examples and cannot show how accurate the app is overall. I checked the Windows launch and a real semantic search locally. A fresh install, hosting online and other operating systems still need checking.

`launch.py` loads PyTorch first because that avoided an error on my machine, and I have not found the cause. Dependencies are pinned in the requirements files, but their own dependencies are not locked.

The project does not train a model, use an LLM API, map to ESCO or have user login. It does not predict hiring decisions.
