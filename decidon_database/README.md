# Database Creation and Schema

## Database Creation

Because individuals frequently held multiple offices, the same person may appear as a deputy in Sycomore, a senator in the Sénat lists, and a minister on Wikipedia. During database construction (executed via run_migration.py), records are consolidated using a deterministic person key. This key prioritizes the Wikidata QID where available, falling back sequentially to the Sénat identifier and the Sycomore identifier. Records without any of these identifiers are grouped using an exact combination of last name, first name, and birth date. Records with the same resulting key are represented by a single person entity.

## Database Schema

The schema is made up of three tables: person, mandate and person_mandate (Figure 1). The person table stores biographical information: first and last name, alias, dates of birth and death, and source identifiers. The mandate table records institutional entities: the institution (Gouvernement, Chambre or Sénat), name,  start and end dates, and Wikipedia and Wikidata identifiers. The junction table person_mandate links individuals to these contexts. It records the person's position, constituency, political party, individual tenure dates, and any additional roles (such as president or stenographer).

<p align="center">
  <img src="../docs/workflow.jpg" width="900" alt="workflow">
  <br>
  <em>
    Figure 1. Workflow from data scraping to database creation.
  </em>
</p>


<p align="center">
  <img src="../db_diagram.jpg" width="400" alt="db_diagram">
  <br>
  <em>
    Figure 1. Schema.
    Source: <a href="https://gallica.bnf.fr/ark:/12148/bpt6k64574218/f1.item">Gallica</a>.
  </em>
</p>

As shown in Figure 2, the database consists of 5,792 individual office holders in the person table, 16,941 political appointments in person_mandate, and 149 institutional entities in mandate.

<p align="center" style="margin-top: 30px;">
  <img src="../db_record_count" width="400" alt="db_record_count">
  <br>
  <em>
    Figure 2. Record count.
    Source: <a href="https://gallica.bnf.fr/ark:/12148/bpt6k64574218/f1.item">Gallica</a>.
  </em>
</p>

This relational architecture cleanly separates individual profiles from the institutional entities and specific service periods in which they operated. A person may hold several successive or simultaneous positions, while a government or legislature includes many people. The person_mandate table represents these relationships and stores attributes that depend on a particular appointment or period of service, rather than on the individual alone. This approach prevents data redundancy by eliminating the need to duplicate biographical entities for every institutional appearance, thereby facilitating cross-institutional career tracking.

SQLite provides a lightweight, self-contained format that is straightforward to distribute and integrate into research workflows. The database can be queried directly, used by command-line or web applications, and exported to other formats.
