"""
Application-level metadata for the DECIDON API.

Endpoint summaries and descriptions are defined in routes.py.
"""

METADATA = {
    "title": "DECIDON — API",
    "version": "0.1.0",
    "description": """
## DECIDON: Prosopography of the French Third Republic

This API provides access to records of deputies, senators, and ministers
of the French Third Republic (1870–1940).

The database distinguishes:

- `person`: an individual office holder;
- `mandate`: an institutional entity, such as a government or legislature;
- `person_mandate`: an individual appointment linking a person to an
  institutional entity, with appointment-specific attributes.

The API provides access to database records.
""",
    "openapi_url": "/api/openapi.json",
    "docs_url": "/api/docs",
    "redoc_url": "/api/redoc",
    "openapi_tags": [
        {
            "name": "persons",
            "description": "Search persons and retrieve their appointments.",
        },
        {
            "name": "mandates",
            "description": (
                "Retrieve institutional entities and their associated persons."
            ),
        },
        {
            "name": "utils",
            "description": "Look up persons by name or alias.",
        },
    ],
}