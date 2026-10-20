# A Database of Office Holders of the French Third Republic to Study Agenda-Setting Dynamics

This repository contains the code used to build a prosopographic database of ministers, deputies, and senators of the French Third Republic (1870–1940). 
It also includes a FastAPI search application and a Whoosh search index for retrieving records from the database.

The database was developed for DECIDON, a research project studying how Parliament and the press influence each other's allocation of attention to policy issues, a process known as agenda-setting.
Understanding how information circulates between Parliament and the press requires structured records of office holders: who they are and, in particular, what position they hold when they speak or are spoken about.

<br><br>

<p align="center">
  <img src="docs/journal_officiel.jpg" width="400" alt="journal_officiel">
  <br>
  <em>
    Figure 1. Verbatim records of parliamentary debates published in the Journal officiel.
    Source: <a href="https://gallica.bnf.fr/ark:/12148/bpt6k64574218/f1.item">Gallica</a>.
  </em>
</p>

## Repository Structure

```text
├── decidon_app/
│   ├── api/            # FastAPI search application
│   └── front-end/      # Web interface
├── decidon_database/   # SQLite database build scripts
├── decidon_index/      # Whoosh search index
├── decidon_scraping/
│   ├── output/         # Scraping outputs and validation reports
│   └── scripts/        # Data scraping, merging, and validation scripts
├── docs/               # Figures
├── README.md           # Project overview
└── requirements.txt    # Python dependencies
```
