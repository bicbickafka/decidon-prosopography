# decidon-prosopography

This repository contains the code used to build a prosopographic database of ministers, deputies, and senators of the French Third Republic (1870–1940). 
It also includes a FastAPI search application and a Whoosh search engine for retrieving prosopographic records from the database.

The database was designed for DECIDON, a research project that studies how Parliament and the press influence each other's allocation of attention to policy issues, a process known as agenda-setting.
To understand how information circulates between Parliament and the press, the researchers need structured data on office holders: who they are and, in particular, what position they hold when they speak or are spoken about. The data are structured in a relational schema, so that named entities extracted from the verbatim accounts of parliamentary sessions and from press articles can be linked to person records and to the offices these persons held.

![Data collection and database-building workflow](docs/journal_officiel.png)

## Repository Structure

```text
├── decidon_scraping/
│   ├── scripts/        # Data scraping, reconciliation, and validation
│   └── output/         # Data outputs and validation reports
├── decidon_app/
│   ├── api/            # FastAPI search application and a Whoosh search engine
│   ├── db_build/       # Relational SQLite database creation
│   └── front-end/      # Frontend development
├── docs/               # Figures
├── requirements.txt    # Python dependencies
└── README.md
```

## Data Sources

The dataset aggregates prosopographic information scraped from three sources: ministers from the [Wikipedia list](fr.wikipedia.org/wiki/Liste_des_gouvernements_de_la_France) of French governments, deputies from [Sycomore]([url](https://www2.assemblee-nationale.fr/sycomore/liste/26)), the Assemblée nationale’s database, and senators from [official lists](senat.fr/senateurs-3eme-republique/senatl.html) published by the Sénat.

## Database Structure

![Relational database schema](docs/db_diagram.png)

| Table | Contents |
|---|---|
| `person` | Names, aliases, birth and death dates, and source identifiers |
| `mandate` | Institutions, offices or legislative terms, dates, and associated identifiers |
| `person_mandate` | Person–office associations, individual tenure dates, constituency, political affiliation, and additional roles |

The model separates identity from appointments: a person is recorded once
and can be linked to multiple offices across institutions. Attributes
that change between appointments belong to `person_mandate`.

This supports career reconstruction, date-based searches for office
holders, and the contextualization of person mentions. Individual tenure
dates may differ from the dates of an office or legislature.

## Getting Started

- To collect and process the data, see
  [decidon_scraping/README.md](decidon_scraping/README.md).
- To build the SQLite database and work with the API, see
  [decidon_app/README.md](decidon_app/README.md).
