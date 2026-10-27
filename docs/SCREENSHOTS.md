# Screenshots

A walkthrough of JobFit Navigator using listings and profiles from my
local testing on 23 October 2026.

[Back to README](../README.md)

## Overview

The overview shows the saved job count, profile statements and required
skills that still need documentation in the selected profile.

![Overview with 22 saved opportunities and 7 profile statements](screenshots/overview.png)

## Job library

Saved listings include their source, company, location, work type and
application status. Selecting a listing opens its full text.

![Saved listings and their details](screenshots/job-library-recent-listings.png)

![Original text of the AI Engineer test listing](screenshots/job-library-listing-details.png)

## Profile

The profile holds skill statements and supporting notes, along with
role interests, preferred locations, work types and language levels.

![Skills and evidence notes](screenshots/profile-skills-evidence.png)

![Job preferences and language statements](screenshots/profile-preferences-languages.png)

## Comparing a job

### Requirements from the same sentence

“Python and SQL are required” marks both skills as Required. The table
shows the job requirement next to the selected profile's documentation,
with the original text below.

![Python and SQL identified as required](screenshots/comparison-coordinated-requirements.png)

### Mixed wording

This test listing calls Python both required and desirable. The app
marks it as Needs review instead of choosing one category.

![Mixed Python requirements marked as Needs review](screenshots/comparison-mixed-requirements.png)

### A different profile and negated requirements

With the `test` profile selected, Python and SQL have no recorded
statements, while Docker has an evidence note. The listing itself
requires Python, treats SQL as desirable and says Docker is not required.

![Job requirements alongside the test profile's documentation](screenshots/comparison-test-profile-negation.png)

### Language requirements

This listing asks for German B2 and describes English as desirable.
The language section shows these separately from technical skills.

![German and English requirement wording](screenshots/comparison-language-requirements.png)

## BM25 keyword search

Searching for `AWS` returns six saved listings. Each result includes
its description and an option to see which words matched.

![BM25 search for AWS](screenshots/search-bm25-aws.png)

The results also include “AWS is not required.” BM25 matches the word;
the comparison page handles its requirement status.

![Matched words and a result containing negated AWS wording](screenshots/search-bm25-explanation.png)

A second example searches for `german` and returns the listing with
German and English requirements.

![BM25 search for german](screenshots/search-bm25-language-query.png)

## Semantic search

The query `transformer` returns ten results in Semantic mode, including
the saved NLP and AI engineering listings.

![Semantic search query and result count](screenshots/search-semantic-query.png)

![Semantic search result cards](screenshots/search-semantic-results.png)

## Browsing by location

Selecting Trier with no search text returns the saved listing for
that location. The result is shown in Browse mode.

![Browsing saved listings by location](screenshots/search-location-browse.png)

## Collection insights

This page brings together requirement counts across the saved jobs.
Each skill has one category per listing, with the selected profile's
documentation shown alongside it.

![Requirement counts across saved jobs](screenshots/collection-insights.png)

The listing traces show where each category comes from. Language
requirement totals appear below them.

![Python listing traces and language totals](screenshots/collection-source-traces-languages.png)

Further rows include desirable skills, skills mentioned as not required,
and wording that needs review.

![Additional skill counts and SQL listing traces](screenshots/collection-additional-concepts.png)

## Further details

See [Architecture](ARCHITECTURE.md) for the application structure and
[Limitations](LIMITATIONS.md) for known gaps.

[Back to README](../README.md)
