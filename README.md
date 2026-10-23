# DECIDON

A prosopographic database and search toolkit for office holders of the French Third Republic (1870–1940).

This repository contains the code used to collect, validate, and consolidate records of deputies, senators, and ministers into a SQLite database. It also includes a FastAPI search application and Whoosh-based search tools for retrieving records and supporting named entity linking.

The database was developed as part of DECIDON, a research project studying how Parliament and the press shape one another’s attention to policy issues—a process known as agenda-setting. Tracking information across these sources requires structured records of political actors: who they were and, in particular, which positions they held when speaking or being spoken about.

## Contents

- [Overview](#overview)
- [Project structure](#project-structure)
- [Installation](#installation)
- [Database construction](#database-construction)
- [Search application](#search-application)
- [Data sources and processing](#data-sources-and-processing)
- [Database schema](#database-schema)
- [Named entity linking](#named-entity-linking)
- [Scope and limitations](#scope-and-limitations)

## Overview

The repository contains three main components:

| Component | Purpose |
|---|---|
| `decidon_scraping` | Collect, merge, and validate source records |
| `decidon_database` | Consolidate person records and construct the SQLite database |
| `decidon_nel` | Provide API access and search tools for named entity linking |

The database contains:

| Table | Records |
|---|---:|
| `person` | 5,792 |
| `person_mandate` | 16,941 |
| `mandate` | 149 |

These counts describe the database version documented here and may change after subsequent data updates.

### Technical stack

| Component | Technology |
|---|---|
| Data processing | Python |
| Database | SQLite |
| ORM | SQLAlchemy |
| API | FastAPI and Pydantic |
| Search index | Whoosh |

## Project structure

```text
.
├── decidon_scraping/
│   ├── scripts/
│   │   ├── deputies.py          # Scrape deputy records
│   │   ├── senators.py          # Scrape senator records
│   │   ├── ministers.py         # Scrape minister records
│   │   ├── merge.py             # Merge source datasets
│   │   └── validate.py          # Generate validation reports
│   └── output/
│       ├── deputies.csv
│       ├── senators.csv
│       ├── ministers.csv
│       └── prosopography.tsv    # Merged source data
├── decidon_database/
│   └── run_migration.py         # Database construction
├── decidon_nel/
│   ├── decidon_app/
│   │   └── api/
│   │       ├── main.py          # FastAPI application entry point
│   │       ├── config.py        # Application settings
│   │       ├── database.py      # SQLAlchemy engine and session
│   │       ├── models.py        # ORM models
│   │       ├── schemas.py       # Pydantic schemas
│   │       ├── crud.py          # Database query logic
│   │       ├── routes.py        # API routes
│   │       └── api_meta.py      # API metadata
│   └── decidon_index/
│       ├── index_gt.py
│       ├── index_infer.py
│       └── index_pre-traite.py
├── docs/                       # Documentation figures
├── .gitignore
├── README.md
└── requirements.txt
```

## Installation

### Prerequisites

- Python 3.10 or later
- pip

Run the following commands from the repository root.

### 1. Create a virtual environment

```bash
python3 -m venv .venv
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```bash
python -m pip install -r requirements.txt
```

## Database construction

The merged source dataset is located at:

```text
decidon_scraping/output/prosopography.tsv
```

The database construction script is located at:

```text
decidon_database/run_migration.py
```

Before running the migration, check the script’s input and output settings:

- the input TSV path should point to the dataset you intend to import;
- the SQLite output path should point to the database you intend to create or update;
- any relative paths must be interpreted from the working directory expected by the script.

From the repository root, the script can be invoked with:

```bash
python decidon_database/run_migration.py
```

After migration, ensure that the API’s database configuration points to the generated SQLite file.

### Record consolidation

Individuals frequently held offices in more than one institution. The same person may therefore appear as a deputy in Sycomore, a senator in the Sénat directory, and a minister on Wikipedia.

During migration, records are consolidated using a deterministic person key. The key uses the first available identifier in the following order:

1. Wikidata QID;
2. Sénat identifier;
3. Sycomore identifier.

Records without any of these identifiers are grouped using an exact combination of last name, first name, and birth date. Records with the same resulting key are represented by a single person entity.

## Search application

The FastAPI application provides programmatic access to person and mandate records through SQLAlchemy. Search parameters include names, date constraints, and office types such as deputy, senator, and minister.

The application code is located in:

```text
decidon_nel/decidon_app/api/
```

Before launching it:

1. Build the database or obtain an existing database file.
2. Check the database configuration in `config.py` and `database.py`.
3. Check the application’s import conventions in `main.py`.

### Development server

For package-relative imports within `api`, launch the application from the repository root with:

```bash
python -m uvicorn api.main:app \
  --app-dir decidon_nel/decidon_app \
  --host 127.0.0.1 \
  --port 8000 \
  --reload
```

If the application instead uses local imports such as `import models`, launch it from its API directory:

```bash
cd decidon_nel/decidon_app/api
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Use the command that matches the imports in the application.

The development server runs at:

```text
http://127.0.0.1:8000
```

### API documentation

Consult `main.py` for the configured Swagger UI and ReDoc URLs, and `routes.py` for the available endpoints and search parameters.

The earlier application documentation used the following documentation paths:

- Swagger UI: `http://127.0.0.1:8000/api/docs`
- ReDoc: `http://127.0.0.1:8000/api/redoc`

Check that these paths are still configured in the current application.

## Data sources and processing

<p align="center">
  <img src="docs/workflow.jpg" width="900" alt="Workflow from source scraping through merging and validation to database creation">
  <br>
  <em>Figure 1. Workflow from data scraping to database creation.</em>
</p>

### Sources

The dataset draws on three main sources, each corresponding to a category of office holders:

| Source | Coverage | Script |
|---|---|---|
| [Sycomore](https://www2.assemblee-nationale.fr/sycomore/recherche) | Deputies | `deputies.py` |
| [Sénat historical directory](https://www.senat.fr/senateurs-3eme-republique/senatl.html) | Senators | `senators.py` |
| [French Wikipedia articles on government compositions](https://fr.wikipedia.org/wiki/Liste_des_gouvernements_de_la_France) | Ministers | `ministers.py` |

Data were scraped in March 2026. The scripts extract biographical information and detailed records of political appointments.

They also retrieve Wikidata QIDs using the Sénat and Sycomore identifiers recorded on Wikidata, or through Wikipedia articles in the case of ministers.

### Merging

`decidon_scraping/scripts/merge.py` combines the three source-specific CSV files into a common TSV dataset.

This step preserves source values and represents unavailable fields as empty values. Deduplication and person-record consolidation are handled during database construction.

The merged dataset is stored at:

```text
decidon_scraping/output/prosopography.tsv
```

### Validation

`decidon_scraping/scripts/validate.py` produces two reports:

| Report | Contents |
|---|---|
| `validation_summary.tsv` | Record counts, field-completeness percentages by institution, and summaries of detected anomalies |
| `validation_issues.tsv` | Potential anomalies in record structure and individual attribute values |

The reports distinguish errors from warnings. Warnings flag cases requiring interpretation checks and do not necessarily indicate incorrect data.

## Database schema

The database separates biographical records, institutional entities, and individual appointments into three tables.

| Table | Purpose | Main attributes |
|---|---|---|
| `person` | Individual office holders | First and last name, alias, birth and death dates, source identifiers |
| `mandate` | Institutional entities, such as governments or legislatures | Institution, name, start and end dates, Wikipedia and Wikidata identifiers |
| `person_mandate` | Appointments linking individuals to institutional entities | Position, constituency, political party, tenure dates, additional roles |

Institution values distinguish `Gouvernement`, `Chambre`, and `Sénat`.

<p align="center">
  <img src="docs/db_diagram.jpg" width="750" alt="Database schema showing person, mandate, and person_mandate tables">
  <br>
  <em>Figure 2. Database schema.</em>
</p>

A person may hold several successive or simultaneous positions, while a government or legislature includes many people. The `person_mandate` junction table represents these relationships and stores attributes associated with a particular appointment rather than with the individual alone.

This separation avoids duplicating biographical records for each institutional appearance and supports cross-institutional career tracking.

<p align="center">
  <img src="docs/db_record_count.jpg" width="750" alt="Record counts for the three database tables">
  <br>
  <em>Figure 3. Database record counts.</em>
</p>

SQLite provides a self-contained database file that can be queried directly, accessed through the API, or incorporated into other research workflows.

## Named entity linking

### Whoosh search index

The search tools support named entity linking by retrieving candidate records for mentions extracted from the *Journal officiel* and press corpora.

The Whoosh index includes:

- names;
- active mandate dates;
- offices;
- constituencies;
- political affiliations.

Queries follow a tiered fallback strategy:

1. exact matching;
2. Boolean `AND`;
3. strong token matching;
4. Boolean `OR`.

Each subsequent tier is attempted when the preceding tier returns no candidates. Candidates are scored using BM25 and restricted according to the session or article date.

<p align="center">
  <img src="docs/nel_fallback_pipeline.jpg" width="900" alt="Tiered Whoosh search strategy from exact matching to Boolean OR">
  <br>
  <em>Figure 4. Whoosh query fallback pipeline with BM25 scoring.</em>
</p>

### Person-level aggregation

Search results are aggregated at the person level using `group_results_by_person`. This brings together appointments belonging to the same individual and supports the interpretation of homonyms, title-only references, and concurrent offices.

For example, Léon Gambetta’s records illustrate overlapping service as Minister of the Interior and deputy in February 1871.

<p align="center">
  <img src="docs/db_gambetta.jpg" width="900" alt="Relational records for Léon Gambetta showing overlapping government and parliamentary appointments">
  <br>
  <em>Figure 5. Relational records for Léon Gambetta during February 1871.</em>
</p>

Person-level aggregation does not, by itself, establish that a mention has been correctly disambiguated. Candidate selection still depends on the available name, date, office, and contextual information.

Once mentions are linked, records can be filtered and aggregated across individuals, appointments, institutions, or political parties.

## Scope and limitations

- Source coverage and field completeness vary across institutions.
- Empty fields represent unavailable values in the merged dataset.
- Record consolidation relies on available identifiers and exact fallback keys; it is not a general fuzzy entity-resolution procedure.
- Different identifiers or variations in names and dates can prevent records referring to the same person from receiving the same key.
- Search results are candidates for entity linking, not independently validated identity assignments.
- Validation warnings require interpretation and should not automatically be treated as errors.
