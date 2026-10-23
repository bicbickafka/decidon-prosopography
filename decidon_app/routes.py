"""
FastAPI routes for the DECIDON database API.
"""

from datetime import date as DateType
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from . import crud, schemas
from .database import get_db

api_router = APIRouter()


@api_router.get("/", include_in_schema=False)
async def read_index():
    index_path = Path(__file__).resolve().parent / "index.html"

    if index_path.is_file():
        return FileResponse(index_path)

    return {
        "service": "DECIDON API",
        "docs": "/api/docs",
    }


@api_router.get(
    "/persons",
    tags=["persons"],
    summary="Search persons by name.",
    description=(
        "Returns paginated biographical records. "
        "The current query applies first-name and last-name filters only; "
        "department, group, and institution are accepted for compatibility "
        "but are not currently applied. "
        "Use /persons/grouped-mandates to search appointments."
    ),
    response_model=list[schemas.PersonOut],
)
def search_persons(
    last_name: str | None = Query(None),
    first_name: str | None = Query(None),
    department: str | None = Query(
        None,
        description="Retained for compatibility; currently not applied.",
    ),
    group: str | None = Query(
        None,
        description="Retained for compatibility; currently not applied.",
    ),
    institution: str | None = Query(
        None,
        description="Retained for compatibility; currently not applied.",
    ),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return crud.search_persons_logic(
        db,
        last_name,
        first_name,
        department,
        group,
        institution,
        limit,
        offset,
    )


@api_router.get(
    "/persons/grouped-mandates",
    tags=["persons"],
    summary="Search persons with their appointments.",
    description=(
        "Returns matching appointments grouped by person. "
        "Supports name, position, political-group, institutional-name, "
        "institution, and date filters. "
        "Appointment lists retain the response field name 'mandate'."
    ),
    response_model=schemas.PersonMandateGroupSearchResponse,
)
def search_grouped_mandates(
    first_name: str | None = Query(None),
    last_name: str | None = Query(None),
    position: str | None = Query(None),
    group_value: str | None = Query(None),
    mandate_name: str | None = Query(None),
    institution: str | None = Query(None),
    start_from: DateType | None = Query(None),
    end_until: DateType | None = Query(None),
    sort_by: str = Query("last_name"),
    sort_dir: str = Query("asc"),
    limit: int = Query(40, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    total_groups = crud.count_person_mandate_groups_logic(
        db,
        first_name,
        last_name,
        position,
        group_value,
        mandate_name,
        institution,
        start_from,
        end_until,
    )

    items = crud.search_person_mandate_groups_logic(
        db,
        first_name,
        last_name,
        position,
        group_value,
        mandate_name,
        institution,
        start_from,
        end_until,
        sort_by,
        sort_dir,
        limit,
        offset,
    )

    return {
        "total_groups": total_groups,
        "limit": limit,
        "offset": offset,
        "items": items,
    }


@api_router.get(
    "/persons/{person_id}",
    tags=["persons"],
    summary="Retrieve a person by ID.",
    description=(
        "Returns a person's biographical record and associated appointments."
    ),
    response_model=schemas.PersonDetailOut,
)
def get_person(person_id: str, db: Session = Depends(get_db)):
    result = crud.get_person_by_id(db, person_id)

    if result is None:
        raise HTTPException(status_code=404, detail="Person not found")

    return result


@api_router.get(
    "/mandates",
    tags=["mandates"],
    summary="List institutional mandates.",
    description=(
        "Returns institutional entities, such as governments or legislatures, "
        "with optional institution and name filters."
    ),
    response_model=list[schemas.MandateEntityOut],
)
def list_mandates(
    institution: str | None = Query(None),
    name: str | None = Query(None),
    db: Session = Depends(get_db),
):
    return crud.list_mandates_logic(db, institution, name)


@api_router.get(
    "/mandates/{mandate_id}/members",
    tags=["mandates"],
    summary="List persons associated with an institutional mandate.",
    description=(
        "Returns distinct persons linked to the specified institutional "
        "entity through person_mandate. "
        "An empty list is returned if no associated persons are found."
    ),
    response_model=list[schemas.PersonOut],
)
def get_members(mandate_id: str, db: Session = Depends(get_db)):
    return crud.get_members_logic(db, mandate_id)


@api_router.get(
    "/lookup",
    tags=["utils"],
    summary="Look up persons by name or alias.",
    description=(
        "Uses SQL LIKE substring matching across last name, first name, "
        "and alias. Returns at most 50 results. This is not fuzzy matching."
    ),
    response_model=list[schemas.PersonOut],
)
def lookup(
    q: str = Query(...),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return crud.lookup_logic(db, q, limit)