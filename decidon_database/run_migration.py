"""Build prosopography.db from scraping/{senators,ministers,deputies}.csv.

Usage: python db_build/run_migration.py
WARNING: drops and recreates all tables on every run.
"""
import hashlib
import os
import re
from datetime import date

import pandas as pd

from app.database import engine, Base, db_session
from app.models import Person, Mandate, PersonMandate

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "scraping")

SOURCES = {
    "senators.csv": "senat",
    "ministers.csv": "gouvernement",
    "deputies.csv": "chambre",
}

OPTIONAL_COLUMNS = ["person_mandate__position", "person_mandate__roles",
                    "person_mandate__group", "person_mandate__constituency",
                    "person__alias", "person__death_date",
                    "person__sycomore_id", "person__senat_id"]


def is_empty(val):
    return pd.isna(val) or str(val).strip() == ""


def clean_str(val):
    return None if is_empty(val) else str(val).strip()


def parse_date(val):
    """YYYY-MM-DD (extra characters ignored) -> date, else None."""
    if is_empty(val):
        return None
    try:
        return date.fromisoformat(str(val).strip()[:10])
    except ValueError:
        return None


def validate_url(url):
    s = clean_str(url)
    return s if s and re.match(r"^https?://", s, re.I) else None


def clean_int_str(val):
    """'844.0' -> '844'."""
    s = clean_str(val)
    if s is None:
        return None
    try:
        return str(int(float(s)))
    except ValueError:
        return s


def make_id(prefix, key):
    return f"{prefix}_{hashlib.sha1(key.encode('utf-8')).hexdigest()[:10]}"


def first_value(series):
    for v in series:
        s = clean_str(v)
        if s is not None:
            return s
    return None


def load_sources(data_dir):
    frames = []
    for filename, institution in SOURCES.items():
        df = pd.read_csv(os.path.join(data_dir, filename), dtype=str)
        df["institution"] = institution
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    for col in OPTIONAL_COLUMNS:
        if col not in df.columns:
            df[col] = None
    return df


def person_key(r):
    # QID first: a person who was deputy then senator is one person across files
    for col in ("person__wikidata_qid", "person__senat_id", "person__sycomore_id"):
        v = clean_str(r[col])
        if v:
            return f"{col}:{v}"
    return "name:" + "|".join(str(clean_str(r[c])) for c in
                              ("person__last_name", "person__first_name", "person__birth_date"))


def mandate_key(r):
    qid = clean_str(r["mandate__wikipedia_qid"])
    return qid or f"{r['mandate__name']}|{r['mandate__start_date']}|{r['mandate__end_date']}"


def check_integrity(df):
    problems = []
    for col in ("mandate__name", "person__last_name"):
        n = df[col].map(is_empty).sum()
        if n:
            problems.append(f"{n} rows with empty {col}")
    if problems:
        raise ValueError("Source data problems: " + "; ".join(problems))


def run_migration():
    df = load_sources(DATA_DIR)
    check_integrity(df)
    print(df.groupby("institution").size().to_string(), "\n")

    df["person_id"] = df.apply(lambda r: make_id("person", person_key(r)), axis=1)
    df["mandate_id"] = df.apply(lambda r: make_id("mandate", mandate_key(r)), axis=1)

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # A. mandate (legislatures / elections / governments)
    for mid, g in df.groupby("mandate_id", sort=False):
        r = g.iloc[0]
        db_session.add(Mandate(
            mandate_id=mid,
            institution=r["institution"],
            name=clean_str(r["mandate__name"]),
            start_date=parse_date(r["mandate__start_date"]),
            end_date=parse_date(r["mandate__end_date"]),
            wikidata_qid=clean_str(r["mandate__wikipedia_qid"]),
            wikipedia_url=validate_url(r["mandate__wikipedia_url"]),
        ))

    # B. person (first non-empty value per field when a person has several rows)
    for pid, g in df.groupby("person_id", sort=False):
        db_session.add(Person(
            person_id=pid,
            last_name=first_value(g["person__last_name"]),
            first_name=first_value(g["person__first_name"]),
            alias=first_value(g["person__alias"]),
            birth_date=parse_date(first_value(g["person__birth_date"])),
            death_date=parse_date(first_value(g["person__death_date"])),
            wikidata_qid=first_value(g["person__wikidata_qid"]),
            wikipedia_url=validate_url(first_value(g["person__wikipedia_url"])),
            sycomore_id=clean_int_str(first_value(g["person__sycomore_id"])),
            senat_id=first_value(g["person__senat_id"]),
        ))
    db_session.flush()

    # C. person_mandate (exact duplicates dropped)
    dedup_cols = ["person_id", "mandate_id", "person_mandate__position",
                  "person_mandate__constituency", "person_mandate__group",
                  "person_mandate__start_date", "person_mandate__end_date",
                  "person_mandate__roles"]
    pm = df.drop_duplicates(subset=dedup_cols)
    for r in pm.itertuples(index=False):
        db_session.add(PersonMandate(
            person_id=r.person_id,
            mandate_id=r.mandate_id,
            position=clean_str(r.person_mandate__position),
            group=clean_str(r.person_mandate__group),
            start_date=parse_date(r.person_mandate__start_date),
            end_date=parse_date(r.person_mandate__end_date),
            constituency=clean_str(r.person_mandate__constituency),
            roles=clean_str(r.person_mandate__roles),
        ))

    db_session.commit()
    print(f"{df.person_id.nunique()} persons, {df.mandate_id.nunique()} mandates, "
          f"{len(pm)} person_mandate rows")


if __name__ == "__main__":
    run_migration()