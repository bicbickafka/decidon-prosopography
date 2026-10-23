# DECIDON Prosopography

A prosopographic database and search application for office holders of the French Third Republic (1870–1940).

The repository builds a structured database of deputies, senators, and ministers, then provides a FastAPI application and Whoosh-based search index for retrieving and linking person records. It was developed as part of **DECIDON**, a research project on agenda-setting dynamics between the French Parliament and the press.

## Overview

Tracking how policy attention circulates between Parliament and the press requires reliable records of political actors: who they were, which offices they held, and when those offices began and ended.

This repository addresses that need by:

- scraping and normalizing biographical and career data from Sycomore, the Sénat’s historical directory, and French Wikipedia;
- consolidating records for individuals who appear in more than one source;
- storing persons, mandates, and appointments in a relational SQLite database;
- exposing the data through a FastAPI search application;
- supporting named entity linking through a Whoosh index with date- and role-aware retrieval.

## Main features

| Component | Description |
|---|---|
| Data pipeline | Scripts for scraping, merging, validating, and migrating source data |
| SQLite database | Relational database of persons, institutional mandates, and appointments |
| Search API | FastAPI + SQLAlchemy interface for querying persons and mandates |
| Entity linking | Whoosh index supporting name, date, office, constituency, and party-based retrieval |
| Validation | Reports on field completeness, structural anomalies, and potential data issues |

## Installation

### Prerequisites

- Python 3.10 or later
- pip

### Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # macOS / Linux
# .\.venv\Scripts\activate  # Windows
```

### Install dependencies

```bash
pip install -r requirements.txt
```

## Database construction

### 1. Add the source data

Place the merged source file at:

```text
db/data/prosopography.tsv
```

### 2. Run the migration

```bash
python3 db/run_migration.py
```

This creates:

```text
db/data/prosopography.db
```

## Launch the application

From the repository root:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The application is then available at:

- Web interface: <http://127.0.0.1:8000>
- Swagger UI: <http://127.0.0.1:8000/api/docs>
- ReDoc: <http://127.0.0.1:8000/api/redoc>

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/persons` | List or search persons |
| `GET` | `/persons/{person_id}` | Retrieve a person by identifier |
| `GET` | `/persons/grouped-mandates` | Search persons with grouped mandates |
| `GET` | `/persons/by-role` | Retrieve persons holding a role on a given date |
| `GET` | `/legislatures` | List legislatures |
| `GET` | `/legislatures/{id}/members` | Retrieve members of a legislature |
| `GET` | `/lookup` | Fuzzy name lookup |

## Project structure

```text
.
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Application settings
│   ├── database.py          # SQLAlchemy engine and session
│   ├── models.py            # ORM models
│   ├── schemas.py           # Pydantic schemas
│   ├── crud.py              # Database query logic
│   ├── routes.py            # API routes
│   ├── api_meta.py          # API metadata
│   └── index.html           # Static frontend
├── db/
│   ├── data/
│   │   ├── prosopography.tsv
│   │   └── prosopography.db
│   └── run_migration.py
├── deputies.py
├── senators.py
├── ministers.py
├── merge.py
├── validate.py
├── docs/
└── requirements.txt
```

## Data sources

| Source | Used for |
|---|---|
| [Sycomore](https://www2.assemblee-nationale.fr/sycomore/recherche) | Deputies of the Third Republic |
| [Sénat historical directory](https://www.senat.fr/senateurs-3eme-republique/senatl.html) | Senators of the Third Republic |
| [French Wikipedia government lists](https://fr.wikipedia.org/wiki/Liste_des_gouvernements_de_la_France) | Ministers and government compositions |
| Wikidata | Persistent identifiers and cross-source matching |

Data were scraped in March 2026 using `deputies.py`, `senators.py`, and `ministers.py`. The scripts extract biographical information, political appointments, and Wikidata QIDs where available.

## Data processing

`merge.py` combines the source-specific CSV files into a common TSV file. Source values are preserved, and unavailable fields are left empty; deduplication and entity resolution occur during migration.

`validate.py` generates two reports:

- `validation_summary.tsv`: record counts, field-completeness rates by institution, and anomaly summaries;
- `validation_issues.tsv`: potential structural and attribute-level issues, separated into errors and warnings.

Warnings flag cases requiring manual interpretation; they do not necessarily indicate incorrect data.

## Data model

The database uses three main tables:

| Table | Purpose |
|---|---|
| `person` | Biographical information and source identifiers |
| `mandate` | Institutional entities: government, Chamber of Deputies, or Senate |
| `person_mandate` | Links between persons and mandates, including role, constituency, party, and tenure dates |

Because individuals may hold several offices—sometimes simultaneously—the same person can be linked to multiple mandates. For example, Léon Gambetta served both as Minister of the Interior and as a deputy in February 1871.

<p align="center">
  <img src="docs/db_diagram.jpg" width="750" alt="Database schema">
  <br>
  <em>Figure 1. Database schema.</em>
</p>

The database contains:

- 5,792 persons;
- 16,941 person–mandate links;
- 149 institutional mandates.

<p align="center">
  <img src="docs/db_record_count.jpg" width="750" alt="Database record counts">
  <br>
  <em>Figure 2. Record counts.</em>
</p>

## Entity linking

The Whoosh index supports named entity linking by matching mentions extracted from the *Journal officiel* and press corpora against database records. Indexed attributes include names, active mandate dates, offices, constituencies, and political affiliations.

Queries use a tiered fallback strategy:

1. exact matching;
2. boolean `AND`;
3. strong token matching;
4. boolean `OR`.

Candidates are scored with BM25 and constrained by session or article date. Results are then grouped at the person level to handle homonyms, title-only references, and overlapping concurrent mandates.

<p align="center">
  <img src="docs/nel_fallback_pipeline.jpg" width="900" alt="Entity-linking fallback pipeline">
  <br>
  <em>Figure 3. Whoosh query fallback pipeline with BM25 scoring.</em>
</p>

## License

Add license information here.
