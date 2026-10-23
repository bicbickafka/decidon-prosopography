# DECIDON: A PROSOPOGRAPHIC DATABASE OF OFFICE HOLDERS OF THE FRENCH THIRD REPUBLIC (1870–1940)

This repository contains the code used to scrape online records of deputies, senators, and ministers of the French Third Republic and build a SQLite database from them. It also includes a FastAPI search application and a Whoosh-based search index for retrieving records and supporting named entity linking.

The database was developed as part of DECIDON, a research project studying how Parliament and the press shaped one another’s attention to policy issues—a process known as agenda-setting. Tracking information across these sources requires structured records of political actors: who they were and, in particular, which positions they held when speaking or being spoken about.

## CONTENTS

1. [Repository structure](#repository-structure)
2. [Installation](#installation)
3. [Data scraping, merging, and validation](#data-scraping-merging-and-validation)
4. [Database creation and schema](#database-creation-and-schema)
5. [FastAPI search application](#fastapi-search-application)
6. [Whoosh search index](#whoosh-search-index)

## REPOSITORY STRUCTURE

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
│   └── run_migration.py         # Database creation
├── decidon_app/
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Application settings
│   ├── database.py             # SQLAlchemy engine and session
│   ├── models.py               # ORM models
│   ├── schemas.py              # Pydantic schemas
│   ├── crud.py                 # Database query logic
│   ├── routes.py               # API routes
│   └── api_meta.py             # API metadata
├── decidon_index/
│   ├── index_gt.py
│   ├── index_infer.py
│   └── index_pre-traite.py
├── docs/                       # Documentation figures
├── .gitignore
├── README.md
└── requirements.txt
```

## INSTALLATION

### PREREQUISITES

- Python 3.10 or later
- pip

Run the following commands from the repository root.

### 1. CREATE A VIRTUAL ENVIRONMENT

```bash
python3 -m venv .venv
```

Activate the environment on macOS or Linux:

```bash
source .venv/bin/activate
```

Or on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. INSTALL DEPENDENCIES

```bash
python -m pip install -r requirements.txt
```

## DATA SCRAPING, MERGING, AND VALIDATION

<p align="center">
  <img src="docs/workflow.jpg" width="900" alt="Workflow from source scraping through merging and validation to database creation">
  <br>
  <em>Figure 1. Workflow from data scraping to database creation.</em>
</p>

### DATA SCRAPING

The dataset draws on three main sources, each corresponding to a category of office holders:

| Source | Coverage | Script |
|---|---|---|
| [Sycomore](https://www2.assemblee-nationale.fr/sycomore/recherche) | Deputies | `deputies.py` |
| [Sénat historical directory](https://www.senat.fr/senateurs-3eme-republique/senatl.html) | Senators | `senators.py` |
| [French Wikipedia articles on government compositions](https://fr.wikipedia.org/wiki/Liste_des_gouvernements_de_la_France) | Ministers | `ministers.py` |

Data were scraped in March 2026. The scripts extract biographical information and detailed records of political appointments.

They also retrieve Wikidata QIDs by matching Sénat and Sycomore identifiers recorded on Wikidata, or through Wikipedia articles in the case of ministers.

### DATA MERGING

`decidon_scraping/scripts/merge.py` combines the three source-specific CSV files into a common TSV dataset.

This step preserves source values and represents unavailable fields as empty values. Deduplication and person-record consolidation are handled during database creation.

The merged dataset is stored at:

```text
decidon_scraping/output/prosopography.tsv
```

### DATA VALIDATION

`decidon_scraping/scripts/validate.py` produces two reports:

| Report | Contents |
|---|---|
| `validation_summary.tsv` | Record counts, field-completeness percentages by institution, and summaries of detected anomalies |
| `validation_issues.tsv` | Potential anomalies in record structure and individual attribute values |

The reports distinguish errors from warnings. Warnings flag cases requiring interpretation checks and do not necessarily indicate incorrect data.

## DATABASE CREATION AND SCHEMA

### DATABASE CREATION

Individuals frequently held offices in more than one institution. The same person may therefore appear as a deputy in Sycomore, a senator in the Sénat directory, and a minister on Wikipedia.

During database creation, records are consolidated using a deterministic person key. The key uses the first available identifier in the following order:

1. Wikidata QID;
2. Sénat identifier;
3. Sycomore identifier.

Records without any of these identifiers are grouped using an exact combination of last name, first name, and birth date. Records with the same resulting key are represented by a single person entity.

The migration script, `decidon_database/run_migration.py`, builds the database from the merged TSV dataset.

Before running it, check that:

- the input TSV path points to `decidon_scraping/output/prosopography.tsv` or your intended source dataset;
- the SQLite output path points to the intended database file;
- relative paths are resolved from the working directory expected by the script.

From the repository root, invoke the script with:

```bash
python decidon_database/run_migration.py
```

After migration, ensure that the API’s database configuration points to the generated SQLite file.

### DATABASE SCHEMA

The database separates biographical records, institutional entities, and individual appointments into three tables:

| Table | Purpose | Main attributes |
|---|---|---|
| `person` | Individual office holders | First and last name, alias, birth and death dates, source identifiers |
| `mandate` | Institutional entities, such as governments or legislatures | Institution, name, start and end dates, Wikipedia and Wikidata identifiers |
| `person_mandate` | Appointments linking individuals to institutional entities | Position, constituency, political party, tenure dates, additional roles |

The institution field distinguishes `Gouvernement`, `Chambre`, and `Sénat`.

<p align="center">
  <img src="docs/db_diagram.jpg" width="750" alt="Database schema showing the person, mandate, and person_mandate tables">
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

## FASTAPI SEARCH APPLICATION

The FastAPI application provides programmatic access to person and mandate records through SQLAlchemy. Search parameters include names, date constraints, and office types such as deputy, senator, and minister.

The application code is located in `decidon_app/`.

Before launching it:

1. Build the database or obtain an existing database file.
2. Check the database configuration in `decidon_app/config.py` and `decidon_app/database.py`.
3. Check the import conventions in `decidon_app/main.py` to select the appropriate launch command below.

### DEVELOPMENT SERVER

If the application uses package-relative imports, such as `from . import models`, launch it from the repository root:

```bash
python -m uvicorn decidon_app.main:app --host 127.0.0.1 --port 8000 --reload
```

If the application uses local imports, such as `import models`, launch it from the application directory:

```bash
cd decidon_app
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

The development server runs at:

```text
http://127.0.0.1:8000
```

### API DOCUMENTATION

Interactive API documentation is available through Swagger UI and ReDoc. Their URLs are configured in `decidon_app/main.py`.

If the original documentation paths have been retained, they are:

- Swagger UI: <http://127.0.0.1:8000/api/docs>
- ReDoc: <http://127.0.0.1:8000/api/redoc>

See `decidon_app/routes.py` for the available endpoints and search parameters.

## WHOOSH SEARCH INDEX

The Whoosh search index supports named entity linking by retrieving candidate records for mentions extracted from the *Journal officiel* and press corpora.

Indexed attributes include:

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
