# DECIDON: Office Holders of the French Third Republic

A prosopographic database of ministers, deputies, and senators of the French Third Republic (1870–1940), with a FastAPI search application and a Whoosh index for Named Entity Linking.

Built for **DECIDON**, a research project on agenda-setting: how Parliament and the press shape one another's attention to policy issues. Tracking that circulation requires structured records of who office holders were and, above all, what position they held when speaking or being spoken about.

**Contents:** [Sources](#sources) · [Stack](#stack) · [Project structure](#project-structure) · [Installation](#installation) · [Data pipeline](#data-pipeline) · [Database](#database) · [Search and NEL](#search-and-named-entity-linking) · [API](#api)

## Sources

| Category | Source |
|---|---|
| Deputies | [Sycomore](https://www2.assemblee-nationale.fr/sycomore/) (Assemblée nationale) |
| Senators | Sénat historical directory |
| Ministers | French Wikipedia articles on government compositions |
| Identifiers | Wikidata (QIDs retrieved via Sénat/Sycomore IDs or Wikipedia articles) |

Data were scraped in March 2026.

## Stack

| Layer | Technology |
|---|---|
| Database | SQLite (3 tables: `person`, `mandate`, `person_mandate`) |
| ORM | SQLAlchemy |
| API | FastAPI + Pydantic |
| Search index | Whoosh (BM25) |
| Frontend | Static HTML / CSS / JS served by FastAPI |

## Project structure

```text
.
├── app/
│   ├── main.py          # FastAPI entry point
│   ├── config.py        # Settings (DB path, etc.)
│   ├── database.py      # SQLAlchemy engine & session
│   ├── models.py        # ORM models
│   ├── schemas.py       # Pydantic schemas
│   ├── crud.py          # Query logic
│   ├── routes.py        # API routes
│   ├── api_meta.py      # API metadata
│   └── index.html       # Frontend (served at /)
├── db/
│   ├── data/
│   │   ├── prosopography.tsv   # Merged source data
│   │   └── prosopography.db    # Generated database
│   └── run_migration.py        # Migration script
├── deputies.py  senators.py  ministers.py   # Scrapers
├── merge.py  validate.py                    # Merging and validation
├── docs/                                    # Figures
└── requirements.txt
```

<!-- Adjust to match the actual layout, including where the Whoosh index and NEL code live. -->

## Installation

Requires Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .\.venv\Scripts\activate
pip install -r requirements.txt
```

### Build the database

Place the merged source file at `db/data/prosopography.tsv`, then run:

```bash
python3 db/run_migration.py
```

This creates `db/data/prosopography.db`.

### Launch the app

From the project root:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The app is served at <http://127.0.0.1:8000>. Interactive docs: [Swagger UI](http://127.0.0.1:8000/api/docs) · [ReDoc](http://127.0.0.1:8000/api/redoc).

## Data pipeline

<p align="center">
<img src="docs/workflow.jpg" width="900" alt="workflow">
<br><em>Figure 1. Workflow from data scraping to database creation.</em>
</p>

**Scraping.** `deputies.py`, `senators.py` and `ministers.py` extract biographical information and detailed records of political appointments, plus Wikidata QIDs.

**Merging.** `merge.py` combines the three CSV files into one TSV. Source values are preserved and unavailable fields left empty; deduplication happens at migration.

**Validation.** `validate.py` writes two reports:
- `validation_summary.tsv`: counts and field completeness per institution (Gouvernement, Chambre, Sénat), plus detected anomalies.
- `validation_issues.tsv`: potential anomalies in structure and attribute values. Errors and warnings are distinguished; warnings flag cases needing interpretation, not necessarily wrong data.

**Consolidation.** `run_migration.py` merges records into one person entity using a deterministic key: Wikidata QID, then Sénat ID, then Sycomore ID. Records with none of these are grouped by exact last name + first name + birth date.

## Database

<p align="center">
<img src="docs/db_diagram.jpg" width="750" alt="db_diagram">
<br><em>Figure 2. Schema.</em>
</p>

| Table | Content |
|---|---|
| `person` | Names, alias, birth/death dates, source identifiers |
| `mandate` | Institutional entities: institution (Gouvernement, Chambre, Sénat), name, dates, Wikipedia/Wikidata IDs |
| `person_mandate` | Links people to mandates: position, constituency, party, tenure dates, additional roles (e.g. president, stenographer) |

Appointment-specific attributes live in `person_mandate`, so biographies are never duplicated and careers can be followed across institutions.

<p align="center">
<img src="docs/db_record_count.jpg" width="750" alt="db_record_count">
<br><em>Figure 3. Record count: 5,792 persons, 16,941 appointments, 149 institutional entities.</em>
</p>

## Search and Named Entity Linking

The database supports NEL by matching entity mentions extracted from the *Journal officiel* and press corpora against its records. A Whoosh index covers names, active mandate dates, offices, constituencies and political affiliations.

Queries use a tiered fallback (exact → boolean AND → strong tokens → boolean OR), moving down a tier only when the previous one returns no candidates. Candidates are scored with BM25 and restricted by session or article date.

<p align="center">
<img src="docs/nel_fallback_pipeline.jpg" width="900" alt="nel_fallback_pipeline">
<br><em>Figure 4. Whoosh query fallback pipeline with BM25 scoring.</em>
</p>

Results are aggregated per person (`group_results_by_person`) to resolve homonyms, title-only references and concurrent mandates, such as Gambetta being both Minister of the Interior and deputy in February 1871.

<p align="center">
<img src="docs/db_gambetta.jpg" width="900" alt="db_gambetta">
<br><em>Figure 5. Léon Gambetta's overlapping mandates, February 1871.</em>
</p>

## API

The search route accepts combinable parameters (name, date constraints, office type) and returns structured person and mandate records.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/persons` | List or search persons |
| GET | `/persons/{person_id}` | Get a person by ID |
| GET | `/persons/grouped-mandates` | Search persons with grouped mandates |
| GET | `/persons/by-role` | Persons holding a role at a given date |
| GET | `/legislatures` | List legislatures |
| GET | `/legislatures/{id}/members` | Members of a legislature |
| GET | `/lookup` | Fuzzy name lookup |

<!-- Verify against routes.py: the endpoints above come from the original README and still use "legislatures". -->
