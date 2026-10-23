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

## Database Creation and Schema

### Database Creation

Because individuals frequently held multiple offices, the same person may appear as a deputy in Sycomore, a senator in the Sénat lists, and a minister on Wikipedia. During database construction (executed via run_migration.py), records are consolidated using a deterministic person key. This key prioritizes the Wikidata QID where available, falling back sequentially to the Sénat identifier and the Sycomore identifier. Records without any of these identifiers are grouped using an exact combination of last name, first name, and birth date. Records with the same resulting key are represented by a single person entity.

### Database Schema

The schema is made up of three tables: person, mandate and person_mandate (Figure 1). The person table stores biographical information: first and last name, alias, dates of birth and death, and source identifiers. The mandate table records institutional entities: the institution (Gouvernement, Chambre or Sénat), name,  start and end dates, and Wikipedia and Wikidata identifiers. The junction table person_mandate links individuals to these entities. It records the person's position, constituency, political party, tenure dates, and any additional roles (such as president or stenographer).

<p align="center">
  <img src="docs/db_diagram.jpg" width="750" alt="db_diagram">
  <br>
  <em>
    Figure 1. Schema.
  </em>
</p>

As shown in Figure 2, the database consists of 5,792 individual office holders in the person table, 16,941 political appointments in person_mandate, and 149 institutional entities in mandate.

<p align="center">
  <img src="docs/db_record_count.jpg" width="750" alt="db_record_count">
  <br>
  <em>
    Figure 2. Record count.
  </em>
</p>

This relational architecture cleanly separates individual profiles from the institutional entities and specific service periods in which they operated. A person may hold several successive or simultaneous positions, while a government or legislature includes many people. The person_mandate table represents these relationships and stores attributes that depend on a particular appointment or period of service, rather than on the individual alone. This approach prevents data redundancy by eliminating the need to duplicate biographical entities for every institutional appearance, thereby facilitating cross-institutional career tracking.

SQLite provides a lightweight, self-contained format that is straightforward to distribute and integrate into research workflows. The database can be queried directly, used by command-line or web applications, and exported to other formats.

## Named Entity Linking

### Whoosh Search Index

The database supports Named Entity Linking (NEL) by querying extracted entity mentions from the Journal officiel and press corpora against database records. The search engine builds a Whoosh index over entity attributes including names, active mandate dates, offices, constituencies, and political affiliations.

To optimize recall and precision, queries follow a tiered fallback strategy (Figure 1): attempting exact matching first, then falling back sequentially to boolean AND, strong token matching, and boolean OR whenever previous tiers return no candidates. Matches across all tiers are scored using BM25 and restricted by session or article date. 

<p align="center">
  <img src="docs//nel_fallback_pipeline.jpg" width="900" alt="nel_fallback_pipeline.jpg">
  <br>
  <em>
    Figure 1. Whoosh search query fallback pipeline with BM25 scoring.
  </em>
</p>

<br>

Search results are aggregated at the person level (group_results_by_person) to resolve homonyms, title-only references, and overlapping concurrent mandates such as Léon Gambetta's simultaneous service as Minister of the Interior and Deputy in February 1871 (Figure 2). Once linked, mentions can be filtered and aggregated across individuals, mandates, institutions, or parties.

<p align="center">
  <img src="docs/db_gambetta.jpg" width="900" alt="db_gambetta.jpg">
  <br>
  <em>
    Figure 2. Relational records for Léon Gambetta during February 1871, illustrating overlapping mandates across government and parliamentary roles.
  </em>
</p>

### FastAPI Search Application

To support reuse, an HTTP search API built with FastAPI and SQLAlchemy provides programmatic access to the database. Its search route accepts combinable parameters, including name, date constraints, and office type (deputy, senator, or minister), and returns structured person and mandate records.  


