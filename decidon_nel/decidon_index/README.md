# Whoosh Search Index

The database supports Named Entity Linking (NEL) by querying extracted entity mentions from the Journal officiel and press corpora against database records. The search engine builds a Whoosh index over entity attributes including names, active mandate dates, offices, constituencies, and political affiliations.

To optimize recall and precision, queries follow a tiered fallback strategy (Figure 1): attempting exact matching first, then falling back sequentially to boolean AND, strong token matching, and boolean OR whenever previous tiers return no candidates. Matches across all tiers are scored using BM25 and restricted by session or article date. 

<p align="center">
  <img src="../../docs//nel_fallback_pipeline.jpg" width="900" alt="nel_fallback_pipeline.jpg">
  <br>
  <em>
    Figure 1. Whoosh search query fallback pipeline with BM25 scoring.
  </em>
</p>

<br>

Search results are aggregated at the person level (group_results_by_person) to resolve homonyms, title-only references, and overlapping concurrent mandates such as Léon Gambetta's simultaneous service as Minister of the Interior and Deputy in February 1871 (Figure 2). Once linked, mentions can be filtered and aggregated across individuals, mandates, institutions, or parties.

<p align="center">
  <img src="../../docs/db_gambetta.jpg" width="900" alt="db_gambetta.jpg">
  <br>
  <em>
    Figure 2. Relational records for Léon Gambetta during February 1871, illustrating overlapping mandates across government and parliamentary roles.
  </em>
</p>

