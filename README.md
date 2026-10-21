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
