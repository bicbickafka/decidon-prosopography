#!/usr/bin/env python3
"""Read-only validation of the merged prosopography TSV.

Uses Python's standard library only.

Default layout:
    decidon_scraping/
    ├── scripts/
    │   └── validate.py
    └── output/
        └── prosopography.tsv

Usage:
    python scripts/validate.py

    python scripts/validate.py \
        --input output/another_file.tsv

    python scripts/validate.py --strict

Reports:
    validation_summary.tsv
    validation_issues.tsv

Reports are replaced on each run.
The input TSV and databases are never modified.

Exit codes:
    0 = no errors
    1 = validation errors, or warnings when --strict is enabled
    2 = input/output failure

Record numbers are 1-based data-record numbers, excluding the header.
They are not physical line numbers when quoted fields contain newlines.
"""

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit


SCRIPT_DIR = Path(__file__).resolve().parent

DEFAULT_INPUT = (
    SCRIPT_DIR.parent
    / "output"
    / "prosopography.tsv"
)

COLUMNS = [
    "mandate__institution",
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

DATE_COLUMNS = [
    column
    for column in COLUMNS
    if column.endswith("_date")
]

PERSON_IDS = [
    "person__wikidata_qid",
    "person__senat_id",
    "person__sycomore_id",
]

ALLOWED_INSTITUTIONS = {
    "senat",
    "chambre",
    "gouvernement",
}

ISSUE_COLUMNS = [
    "severity",
    "check",
    "record",
    "institution",
    "person_qid",
    "senat_id",
    "sycomore_id",
    "field",
    "value",
    "message",
]

SUMMARY_COLUMNS = [
    "section",
    "name",
    "institution",
    "count",
    "total",
    "percent",
]


def validate(input_path, report_dir, strict=False):
    """Validate the TSV, write reports, and return an exit code."""
    issues = []
    summary = []

    def issue(
        severity,
        check,
        number=0,
        row=None,
        field="",
        value="",
        message="",
    ):
        """Append one issue to the detailed report."""
        row = row or {}

        issues.append({
            "severity": severity,
            "check": check,
            "record": number or "",
            "institution": row.get("mandate__institution", ""),
            "person_qid": row.get("person__wikidata_qid", ""),
            "senat_id": row.get("person__senat_id", ""),
            "sycomore_id": row.get("person__sycomore_id", ""),
            "field": field,
            "value": value,
            "message": message,
        })

    def stat(
        section,
        name,
        institution="",
        count=0,
        total="",
        percent="",
    ):
        """Append one metric to the summary report."""
        summary.append({
            "section": section,
            "name": name,
            "institution": institution,
            "count": count,
            "total": total,
            "percent": percent,
        })

    # --------------------------------------------------------------
    # 1. Read the TSV and validate its structure
    # --------------------------------------------------------------

    rows = []

    with input_path.open(
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        reader = csv.reader(
            handle,
            delimiter="\t",
            strict=True,
        )

        try:
            header = next(reader, [])

            if not header:
                issue(
                    "ERROR",
                    "empty_file",
                    message="No TSV header found.",
                )

            else:
                for column, count in Counter(header).items():
                    if count > 1:
                        issue(
                            "ERROR",
                            "duplicate_column",
                            field=column,
                            value=count,
                        )

                for column in sorted(set(COLUMNS) - set(header)):
                    issue(
                        "ERROR",
                        "missing_column",
                        field=column,
                    )

                for column in sorted(set(header) - set(COLUMNS)):
                    issue(
                        "ERROR",
                        "unexpected_column",
                        field=column,
                    )

                if header[0] != "mandate__institution":
                    issue(
                        "ERROR",
                        "institution_not_first",
                        value=header[0],
                        message=(
                            "The first column must be "
                            "mandate__institution."
                        ),
                    )

                if (
                    set(header) == set(COLUMNS)
                    and header != COLUMNS
                ):
                    issue(
                        "WARNING",
                        "column_order",
                        message=(
                            "Column order differs from the "
                            "expected merge.py output."
                        ),
                    )

                for number, values in enumerate(reader, 1):
                    if len(values) != len(header):
                        issue(
                            "ERROR",
                            "record_width",
                            number=number,
                            value=len(values),
                            message=(
                                f"Expected {len(header)} fields; "
                                "record skipped."
                            ),
                        )
                        continue

                    rows.append((
                        number,
                        dict(zip(header, values)),
                    ))

        except csv.Error as exc:
            issue(
                "ERROR",
                "tsv_parse",
                message=(
                    f"Near physical line {reader.line_num}: {exc}"
                ),
            )

    stat(
        "counts",
        "valid_width_records",
        count=len(rows),
    )

    if not rows:
        issue(
            "ERROR",
            "no_data",
            message="No usable data records found.",
        )

    schema_ok = (
        set(COLUMNS).issubset(header)
        and len(header) == len(set(header))
    )

    # Field checks require a complete, unambiguous schema.
    if schema_ok:

        # ----------------------------------------------------------
        # 2. Validate individual records
        # ----------------------------------------------------------

        for number, original_row in rows:
            # Strip only in memory; source values remain unchanged.
            row = {
                key: value.strip()
                for key, value in original_row.items()
            }

            institution = row["mandate__institution"]

            if institution not in ALLOWED_INSTITUTIONS:
                issue(
                    "ERROR",
                    "institution",
                    number,
                    row,
                    "mandate__institution",
                    institution,
                    "Expected senat, chambre or gouvernement.",
                )

            for column in COLUMNS:
                if original_row[column] != row[column]:
                    issue(
                        "WARNING",
                        "outer_whitespace",
                        number,
                        row,
                        column,
                        original_row[column],
                    )

            for column in [
                "mandate__name",
                "person__last_name",
            ]:
                if not row[column]:
                    issue(
                        "ERROR",
                        "missing_required",
                        number,
                        row,
                        column,
                    )

            for column in [
                "person__first_name",
                "person__birth_date",
                "person_mandate__start_date",
                "person_mandate__end_date",
            ]:
                if not row[column]:
                    issue(
                        "WARNING",
                        "missing_value",
                        number,
                        row,
                        column,
                    )

            for expected_institution, column in [
                ("senat", "person__senat_id"),
                ("chambre", "person__sycomore_id"),
            ]:
                if (
                    institution == expected_institution
                    and not row[column]
                ):
                    issue(
                        "WARNING",
                        "missing_institution_id",
                        number,
                        row,
                        column,
                    )

            if not any(row[column] for column in PERSON_IDS):
                issue(
                    "WARNING",
                    "no_person_identifier",
                    number,
                    row,
                    message=(
                        "Person matching would require "
                        "a name-based fallback."
                    ),
                )

            # Identifier syntax
            for column in [
                "person__wikidata_qid",
                "mandate__wikipedia_qid",
            ]:
                value = row[column]

                if value and not re.fullmatch(
                    r"Q[1-9][0-9]*",
                    value,
                ):
                    issue(
                        "ERROR",
                        "qid_format",
                        number,
                        row,
                        column,
                        value,
                    )

            column = "person__sycomore_id"
            value = row[column]

            if value and not re.fullmatch(r"[0-9]+", value):
                issue(
                    "ERROR",
                    "sycomore_format",
                    number,
                    row,
                    column,
                    value,
                    (
                        "Expected digits only; decimal-form "
                        "identifiers need review."
                    ),
                )

            # Basic URL syntax, without network requests
            for column in [
                "person__wikipedia_url",
                "mandate__wikipedia_url",
            ]:
                value = row[column]

                if not value:
                    continue

                try:
                    url = urlsplit(value)

                    valid = (
                        url.scheme in {"http", "https"}
                        and bool(url.hostname)
                        and not re.search(r"\s", value)
                    )

                except ValueError:
                    valid = False

                if not valid:
                    issue(
                        "WARNING",
                        "url_format",
                        number,
                        row,
                        column,
                        value,
                        (
                            "Syntax check only; "
                            "no network request performed."
                        ),
                    )

            # Strict ISO dates and calendar validity
            dates = {}

            for column in DATE_COLUMNS:
                value = row[column]

                if not value:
                    continue

                try:
                    if not re.fullmatch(
                        r"[0-9]{4}-[0-9]{2}-[0-9]{2}",
                        value,
                    ):
                        raise ValueError()

                    dates[column] = date.fromisoformat(value)

                except ValueError:
                    issue(
                        "ERROR",
                        "date_format",
                        number,
                        row,
                        column,
                        value,
                        (
                            "Expected a valid calendar date "
                            "in YYYY-MM-DD format."
                        ),
                    )

            # Internal date ordering
            date_pairs = [
                (
                    "mandate__start_date",
                    "mandate__end_date",
                ),
                (
                    "person_mandate__start_date",
                    "person_mandate__end_date",
                ),
                (
                    "person__birth_date",
                    "person__death_date",
                ),
            ]

            for start_column, end_column in date_pairs:
                if (
                    start_column in dates
                    and end_column in dates
                    and dates[end_column] < dates[start_column]
                ):
                    issue(
                        "ERROR",
                        "reversed_dates",
                        number,
                        row,
                        end_column,
                        row[end_column],
                        (
                            f"Earlier than {start_column}: "
                            f"{row[start_column]}."
                        ),
                    )

            # Membership dates versus biographical dates
            for column in [
                "person_mandate__start_date",
                "person_mandate__end_date",
            ]:
                for boundary, relation in [
                    ("person__birth_date", "before_birth"),
                    ("person__death_date", "after_death"),
                ]:
                    if column not in dates or boundary not in dates:
                        continue

                    if relation == "before_birth":
                        invalid = dates[column] < dates[boundary]
                    else:
                        invalid = dates[column] > dates[boundary]

                    if invalid:
                        issue(
                            "WARNING",
                            relation,
                            number,
                            row,
                            column,
                            row[column],
                            (
                                f"Compare {boundary}: "
                                f"{row[boundary]}."
                            ),
                        )

            # Electoral-event dates are deliberately not treated
            # as mandatory boundaries for individual service.

        normalized = [
            (
                number,
                {
                    key: value.strip()
                    for key, value in row.items()
                },
            )
            for number, row in rows
        ]

        # ----------------------------------------------------------
        # 3. Counts and coverage by institution
        # ----------------------------------------------------------

        institutions = sorted({
            row["mandate__institution"]
            for _, row in normalized
        })

        for institution in institutions:
            group = [
                row
                for _, row in normalized
                if row["mandate__institution"] == institution
            ]

            stat(
                "counts",
                "records",
                institution,
                len(group),
            )

            for column in COLUMNS:
                filled = sum(
                    bool(row[column])
                    for row in group
                )

                stat(
                    "coverage",
                    column,
                    institution,
                    filled,
                    len(group),
                    f"{100 * filled / len(group):.2f}",
                )

        # ----------------------------------------------------------
        # 4. Exact duplicate records
        # ----------------------------------------------------------

        seen = {}

        for number, row in rows:
            key = tuple(row[column] for column in COLUMNS)

            if key in seen:
                issue(
                    "WARNING",
                    "exact_duplicate",
                    number,
                    row,
                    message=(
                        "Identical source values to "
                        f"record {seen[key]}."
                    ),
                )

            else:
                seen[key] = number

        # ----------------------------------------------------------
        # 5. Attribute conflicts under a shared identifier
        # ----------------------------------------------------------

        def conflicts(id_column, fields, label):
            """Report differing nonempty values under a shared ID."""
            groups = defaultdict(list)

            for number, row in normalized:
                identifier = row[id_column]

                if identifier:
                    groups[identifier].append((number, row))

            for identifier, group in groups.items():
                for field in fields:
                    values = sorted({
                        row[field]
                        for _, row in group
                        if row[field]
                    })

                    if len(values) <= 1:
                        continue

                    detail = json.dumps(
                        values,
                        ensure_ascii=False,
                    )

                    for number, row in group:
                        if row[field]:
                            issue(
                                "WARNING",
                                label,
                                number,
                                row,
                                field,
                                row[field],
                                (
                                    f"{id_column}={identifier}; "
                                    "conflicting nonempty values: "
                                    f"{detail}"
                                ),
                            )

            return groups

        for id_column in PERSON_IDS:
            other_identifiers = [
                column
                for column in PERSON_IDS
                if column != id_column
            ]

            fields = other_identifiers + [
                "person__last_name",
                "person__first_name",
                "person__birth_date",
                "person__death_date",
            ]

            groups = conflicts(
                id_column,
                fields,
                "person_conflict",
            )

            # Possible first-name / last-name reversal
            for identifier, group in groups.items():
                name_pairs = defaultdict(list)

                for number, row in group:
                    pair = (
                        row["person__last_name"].casefold(),
                        row["person__first_name"].casefold(),
                    )

                    if all(pair):
                        name_pairs[pair].append((number, row))

                for pair, members in name_pairs.items():
                    reversed_pair = pair[::-1]

                    if (
                        pair[0] != pair[1]
                        and reversed_pair in name_pairs
                    ):
                        for number, row in members:
                            issue(
                                "WARNING",
                                "possible_name_reversal",
                                number,
                                row,
                                message=(
                                    "Reversed name pair also exists "
                                    f"for {id_column}={identifier}."
                                ),
                            )

        conflicts(
            "mandate__wikipedia_qid",
            [
                "mandate__institution",
                "mandate__name",
                "mandate__start_date",
                "mandate__end_date",
            ],
            "mandate_conflict",
        )

        # ----------------------------------------------------------
        # 6. Candidate duplicate memberships
        # ----------------------------------------------------------

        # Group independently under each identifier. This avoids
        # inventing resolved person IDs during validation.
        for id_column in PERSON_IDS:
            groups = defaultdict(list)

            for number, row in normalized:
                mandate = row["mandate__wikipedia_qid"]

                if not mandate:
                    mandate = json.dumps([
                        row["mandate__name"],
                        row["mandate__start_date"],
                        row["mandate__end_date"],
                    ])

                if not (
                    row[id_column]
                    and row["person_mandate__start_date"]
                    and row["person_mandate__end_date"]
                ):
                    continue

                key = (
                    row[id_column],
                    row["mandate__institution"],
                    mandate,
                    row["person_mandate__start_date"],
                    row["person_mandate__end_date"],
                )

                groups[key].append((number, row))

            for key, group in groups.items():
                if len(group) <= 1:
                    continue

                numbers = [
                    number
                    for number, _ in group
                ]

                for number, row in group:
                    issue(
                        "WARNING",
                        "membership_candidate",
                        number,
                        row,
                        id_column,
                        key[0],
                        (
                            "Shared person identifier, mandate "
                            f"and dates; records {numbers}. "
                            "Not necessarily duplicates: compare "
                            "positions, roles, groups "
                            "and constituencies."
                        ),
                    )

    # --------------------------------------------------------------
    # 7. Summarize results
    # --------------------------------------------------------------

    severity_counts = Counter(
        item["severity"]
        for item in issues
    )

    check_counts = Counter(
        (item["severity"], item["check"])
        for item in issues
    )

    for (severity, check), count in sorted(check_counts.items()):
        stat(
            "issues",
            f"{severity}:{check}",
            count=count,
        )

        print(
            f"[{severity}] {check}: "
            f"{count} issue entries"
        )

    for severity in ["ERROR", "WARNING"]:
        stat(
            "totals",
            severity,
            count=severity_counts[severity],
        )

    # --------------------------------------------------------------
    # 8. Write reports, never replacing the input
    # --------------------------------------------------------------

    reports = [
        (
            "validation_issues.tsv",
            ISSUE_COLUMNS,
            issues,
        ),
        (
            "validation_summary.tsv",
            SUMMARY_COLUMNS,
            summary,
        ),
    ]

    for filename, _, _ in reports:
        destination = report_dir / filename

        if destination.resolve() == input_path.resolve():
            raise ValueError(
                "Report path must not replace the input TSV."
            )

    report_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    for filename, columns, data in reports:
        destination = report_dir / filename

        with destination.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=columns,
                delimiter="\t",
            )

            writer.writeheader()
            writer.writerows(data)

    print(f"\nInput: {input_path}")
    print(f"Usable records: {len(rows):,}")

    print(
        f"Errors: {severity_counts['ERROR']:,}; "
        f"warnings: {severity_counts['WARNING']:,}"
    )

    print(
        "Counts are issue entries, not distinct records; "
        "one record can have several issues."
    )

    print(f"Reports: {report_dir}")

    failed = (
        severity_counts["ERROR"] > 0
        or (
            strict
            and severity_counts["WARNING"] > 0
        )
    )

    return int(failed)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=(
            "Merged TSV to validate "
            f"(default: {DEFAULT_INPUT})."
        ),
    )

    parser.add_argument(
        "--report-dir",
        type=Path,
        help=(
            "Report directory "
            "(default: directory containing the input TSV)."
        ),
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 for warnings as well as errors.",
    )

    args = parser.parse_args()

    input_path = args.input.expanduser().resolve()

    report_dir = (
        args.report_dir.expanduser().resolve()
        if args.report_dir is not None
        else input_path.parent
    )

    try:
        return validate(
            input_path,
            report_dir,
            strict=args.strict,
        )

    except (OSError, UnicodeError, ValueError) as exc:
        print(
            f"Error: {exc}",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())