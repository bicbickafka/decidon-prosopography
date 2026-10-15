# DECIDON — Database and search API

A SQLite database-building script and a FastAPI application for querying
office holders of the French Third Republic.

The API uses SQLAlchemy to access the database. It is intended to support
searches combining names, temporal constraints, and types of office.

See the [main README](../README.md) for coverage, sources, and limitations.

## Structure

```text
decidon_app/
├── api/                    # API implementation and indexing scripts
├── db_build/
│   ├── run_migration.py    # Database-building script
│   └── prosopography.db    # SQLite database
└── front-end/              # Reserved for frontend development
```

## Database

![Relational database schema](../docs/db_diagram.png)

| Table | Contents |
|---|---|
| `person` | Biographical information and source identifiers |
| `mandate` | Institutional offices or legislative terms |
| `person_mandate` | Person–office associations and individual tenure details |

The version described in the data paper contains:

- 5,792 records in `person`.
- 149 records in `mandate`.
- 16,941 records in `person_mandate`.

These figures may change with updated inputs.

## Build the database

The database-building stage connects the following files:

| Role | Repository path |
|---|---|
| Input | `decidon_scraping/output/prosopography.tsv` |
| Script | `decidon_app/db_build/run_migration.py` |
| Output | `decidon_app/db_build/prosopography.db` |

Paths above are relative to the repository root.

Preserve a copy of the existing database before running the script.
Its handling of existing tables and records must be verified before
rebuilding.

After a rebuild, check table counts, relationships, and sample records
against the input. Matching record counts alone does not establish that
two database versions are identical.

For input preparation and validation, see the
[collection README](../decidon_scraping/README.md).

## Setup and execution status

The supported Python version, dependencies, configuration, and startup
command are being verified against the current code.

Before running the application, confirm:

- The configured path points to the intended SQLite database.
- Any required search indexes have been built.
- The working directory and imports match the current folder layout.

Tested installation, database-building, and startup commands will b
eadded here. Commands from earlier project layouts should not be assumed
to work unchanged.

## API documentation

Routes, query parameters, response formats, and interactive documentation
URLs are being verified against the implementation.

No public deployment URL is currently documented.

Temporal searches should account for missing dates and simultaneous
appointments. Identifying a person does not necessarily establish the
capacity in which they appear in a historical text.

## Frontend

The `front-end/` directory is currently empty. No browser-based interface
is included in the current implementation.

## Related documentation

- [Project overview](../README.md)
- [Data collection and processing](../decidon_scraping/README.md)