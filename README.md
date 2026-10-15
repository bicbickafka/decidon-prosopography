# decidon-prosopography

A Database of Office Holders of the French Third Republic to Study Agenda-Setting Dynamics

A SQLite database of deputies, senators, and ministers during the French
Third Republic (1870–1940), with collection and processing scripts and a
search API.

Developed for DECIDON, the resource supports research into agenda-setting
dynamics between Parliament and the press. It provides a reference layer
for linking person mentions in parliamentary debates and press articles
to historical office holders.

![Data collection and database-building workflow](docs/journal_officiel.png)


![Data collection and database-building workflow](docs/workflow.png)

## Data Sources

Data were collected in March 2026 from three sources:

| Office holders | Source |
|---|---|
| Deputies | [Sycomore, Assemblée nationale](https://www2.assemblee-nationale.fr/sycomore/liste/) |
| Senators | [Sénat: senators of the Third Republic](https://www.senat.fr/senateurs-3eme-republique/senatl.html) |
| Ministers | [French Wikipedia: list of French governments](https://fr.wikipedia.org/wiki/Liste_des_gouvernements_de_la_France) |

Ministers are included whether or not they also sat in either chamber.

The version described in the accompanying data paper contains 5,792
people, 149 offices or legislative terms, and 16,941 person–office
associations.

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

## Repository Structure

```text
.
├── decidon_scraping/
│   ├── scripts/        # Collection, merging, and validation
│   └── output/         # CSVs, merged TSV, and validation reports
├── decidon_app/
│   ├── api/            # Search API and indexing scripts
│   ├── db_build/       # Database-building script and SQLite database
│   └── front-end/      # Reserved for frontend development
├── docs/               # Schema and workflow figures
├── requirements.txt
└── README.md
```

## Getting Started

- To collect and process the data, see
  [decidon_scraping/README.md](decidon_scraping/README.md).
- To build the SQLite database and work with the API, see
  [decidon_app/README.md](decidon_app/README.md).
