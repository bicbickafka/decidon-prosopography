# Data Scraping, Merging, and Validation

<br><br>

<p align="center">
  <img src="../docs/workflow.jpg" width="900" alt="workflow">
  <br>
  <em>
    Figure 1. Workflow from data scraping to database creation.
  </em>
</p>

## Data Scraping

The dataset draws on three sources, each corresponding to a category of office holders: Sycomore for deputies, the Sénat’s historical directory for senators, and the French-language Wikipedia articles on government compositions for ministers. Data were scraped in March 2026 using the deputies.py, senators.py, and ministers.py scripts, respectively. The scripts extract biographical information and detailed records of political appointments. Additionally, the scripts retrieve Wikidata QIDs via the Sénat and Sycomore identifiers embedded in politicians' Wikidata pages, or via Wikipedia articles in the case of ministers.

##  Data Merging
The three source-specific CSV files are combined into a common TSV file via merge.py. This step preserves source values and represents unavailable fields as empty values; deduplication and entity resolution are handled during the subsequent migration phase.

##  Data Validation
validate.py produces two reports. validation_summary.tsv provides counts and field-completeness percentages across institutions (Gouvernement, Chambre, and Sénat), alongside summaries of detected anomalies. validation_issues.tsv flags potential data anomalies across structural records and individual attribute values. Errors and warnings are distinguished; warnings identify cases requiring interpretation checks and do not necessarily indicate incorrect data.
