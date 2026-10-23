# A Database of Office Holders of the French Third Republic to Study Agenda-Setting Dynamics

This repository contains the code used to build a prosopographic database of ministers, deputies, and senators of the French Third Republic (1870–1940). 
It also includes a FastAPI search application and a Whoosh search index for retrieving records from the database.

The database was developed as part of DECIDON, a research project studying how Parliament and the press shape one another’s attention to policy issues—a process known as agenda-setting.
Tracking how information circulates between Parliament and the press requires structured records of office holders: who they were and, in particular, what position they held when speaking or being spoken about. This database was created to fulfill that need.

## Repository Structure

```text
├── decidon_database/   # SQLite database build scripts
├── decidon_nel/        
│   ├── api/            # FastAPI search application
│   ├── front-end/      # Web interface
│   └── index/          # Whoosh search index
├── decidon_scraping/
│   ├── output/         # Scraping outputs and validation reports
│   └── scripts/        # Data scraping, merging, and validation scripts
├── docs/               # Figures
├── README.md           # Project overview
└── requirements.txt    # Python dependencies
```
## Data Scraping, Merging, and Validation

<br>

<p align="center">
  <img src="docs/workflow.jpg" width="900" alt="workflow">
  <br>
  <em>
    Figure 1. Workflow from data scraping to database creation.
  </em>
</p>

### Data Scraping

The dataset draws on three sources, each corresponding to a category of office holders: [Sycomore](https://www2.assemblee-nationale.fr/sycomore/recherche) for deputies, [the Sénat’s historical directory](https://www.senat.fr/senateurs-3eme-republique/senatl.html) for senators, and [the French-language Wikipedia articles on government compositions](https://fr.wikipedia.org/wiki/Liste_des_gouvernements_de_la_France) for ministers. Data were scraped in March 2026 using the deputies.py, senators.py, and ministers.py scripts, respectively. The scripts extract biographical information and detailed records of political appointments. Additionally, the scripts retrieve Wikidata QIDs via the Sénat and Sycomore identifiers embedded in politicians' Wikidata pages, or via Wikipedia articles in the case of ministers.

###  Data Merging
The three source-specific CSV files are combined into a common TSV file via merge.py. This step preserves source values and represents unavailable fields as empty values; deduplication and entity resolution are handled during the subsequent migration phase.

###  Data Validation
validate.py produces two reports. validation_summary.tsv provides counts and field-completeness percentages across institutions (Gouvernement, Chambre, and Sénat), alongside summaries of detected anomalies. validation_issues.tsv flags potential data anomalies across structural records and individual attribute values. Errors and warnings are distinguished; warnings identify cases requiring interpretation checks and do not necessarily indicate incorrect data.
