#!/usr/bin/env python3
"""Combine senators.csv, deputies.csv and ministers.csv into one TSV.

Default input directory:
    decidon_scraping/output/

Default output:
    decidon_scraping/output/prosopography.tsv

This script does not modify a database, correct source values,
resolve person identities, or remove duplicate rows.
"""

import argparse
from pathlib import Path

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent / "output"

SOURCES = (
    ("senators.csv", "senat"),
    ("deputies.csv", "chambre"),
    ("ministers.csv", "gouvernement"),
)

COLUMNS = [
    "mandate__name",
    "mandate__start_date",
    "mandate__end_date",
    "mandate__wikipedia_qid",
    "mandate__wikipedia_url",
    "person_mandate__position",
    "person_mandate__constituency",
    "person_mandate__group",
    "person_mandate__roles",
    "person_mandate__start_date",
    "person_mandate__end_date",
    "person__last_name",
    "person__first_name",
    "person__alias",
    "person__birth_date",
    "person__death_date",
    "person__sycomore_id",
    "person__senat_id",
    "person__wikidata_qid",
    "person__wikipedia_url",
]

REQUIRED_COLUMNS = {
    "mandate__name",
    "person__last_name",
}


def load_source(path, institution):
    """Read one CSV while preserving identifiers and dates as strings."""
    df = pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig",
    )

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"{path.name}: missing required columns: "
            + ", ".join(sorted(missing))
        )

    unexpected = set(df.columns) - set(COLUMNS)
    if unexpected:
        raise ValueError(
            f"{path.name}: unexpected columns; update COLUMNS first: "
            + ", ".join(sorted(unexpected))
        )

    # Fill columns absent from this source with empty strings.
    df = df.reindex(columns=COLUMNS, fill_value="")
    df.insert(0, "mandate__institution", institution)

    return df


def merge_sources(data_dir, output, overwrite=False):
    """Combine all source rows and write the resulting TSV."""
    sources = [
        (data_dir / filename, institution)
        for filename, institution in SOURCES
    ]

    missing_files = [
        str(path)
        for path, _ in sources
        if not path.is_file()
    ]
    if missing_files:
        raise FileNotFoundError(
            "Missing source files:\n" + "\n".join(missing_files)
        )

    source_paths = {path.resolve() for path, _ in sources}
    if output.resolve() in source_paths:
        raise ValueError("The output must not replace a source CSV.")

    if output.exists() and not overwrite:
        raise FileExistsError(
            f"Output already exists: {output}\n"
            "Choose another output name or pass --overwrite."
        )

    frames = []

    for path, institution in sources:
        df = load_source(path, institution)
        frames.append(df)
        print(f"{path.name}: {len(df):,} rows ({institution})")

    merged = pd.concat(frames, ignore_index=True)

    output.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(
        output,
        sep="\t",
        index=False,
        encoding="utf-8",
        mode="w" if overwrite else "x",
    )

    print(f"\nWritten: {output}")
    print(f"Total rows: {len(merged):,}")
    print(f"Total columns: {len(merged.columns)}")
    print("No source values corrected; no rows removed.")
    print("No database created or modified.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DATA_DIR,
        help=f"CSV input directory (default: {DATA_DIR}).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Output TSV path "
            "(default: DATA_DIR/prosopography.tsv)."
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacement of an existing output TSV.",
    )

    args = parser.parse_args()

    data_dir = args.data_dir.expanduser().resolve()
    output = (
        args.output.expanduser().resolve()
        if args.output is not None
        else data_dir / "prosopography.tsv"
    )

    try:
        merge_sources(data_dir, output, overwrite=args.overwrite)
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()