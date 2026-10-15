#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Recherche chaque mention PER/SPK d'un export Label Studio pré-traité dans
l'index Whoosh DECIDON, avec le moteur DecidonSearchEngine partagé entre
toutes les mentions et un filtre de date par séance (data.meta.date_iso).
Sortie : même export, avec "persons" ajouté à chaque mention liée.

Seules les mentions PER et SPK sont liées ; les autres labels (TITL, COM,
FCT, etc.) et les relations restent inchangés.

Usage:
python3 index_pre-traite.py \
    --json tests/2026-07-01_export_label-studio_NER-NEL_pre-traite.json \
    --output-json tests/2026-07-01_export_label-studio_NER-NEL_pre-traite_linked.json
"""

from __future__ import annotations

import argparse
import json
import time as time_module
from typing import Any

from index_infer import DecidonSearchEngine, group_results_by_person

LABELS_TO_LINK = {"PER", "SPK"}


def load_label_studio_export(filename: str) -> list[dict[str, Any]]:
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("L'export Label Studio doit avoir une liste en racine.")
    return data


def run_pretraite_scaled(
    filename: str,
    bool_type: str = "AND",
    limit: int = 10,
    verbose: bool = False,
) -> list[dict[str, Any]]:
    tasks = load_label_studio_export(filename)

    # Collecte des mentions PER/SPK a lier : (session_date, resultat)
    mentions: list[tuple[str | None, dict[str, Any]]] = []
    for task in tasks:
        meta = (task.get("data") or {}).get("meta") or {}
        if isinstance(meta, str):  # securite si meta est serialise en texte
            try:
                meta = json.loads(meta)
            except json.JSONDecodeError:
                meta = {}
        session_date = meta.get("date_iso")
        for annotation in task.get("annotations", []):
            for res in annotation.get("result", []):
                if res.get("type") != "labels":
                    continue
                labels = set((res.get("value") or {}).get("labels", []))
                if not labels & LABELS_TO_LINK:
                    continue
                mentions.append((session_date, res))

    # Regroupement par date, comme index_gt.py
    by_date: dict[str | None, list[dict[str, Any]]] = {}
    for session_date, res in mentions:
        by_date.setdefault(session_date, []).append(res)

    print(f"{len(tasks)} taches, {len(mentions)} mentions, {len(by_date)} dates distinctes")
    print(f"labels={sorted(LABELS_TO_LINK)} bool_type={bool_type} limit={limit}")

    engine = DecidonSearchEngine(bool_type=bool_type)

    start = time_module.time()
    total_results = 0
    empty_queries = 0

    try:
        for session_date, results in by_date.items():
            print(f"-- session_date={session_date} ({len(results)} mentions) --")

            for res in results:
                text_value = (res["value"].get("text") or "").strip()

                if not text_value:
                    res["persons"] = []
                    empty_queries += 1
                    continue

                raw_results = engine.search(
                    text_value,
                    session_date=session_date,
                    limit=limit,
                )
                persons = group_results_by_person(raw_results)
                res["persons"] = persons

                total_results += len(persons)
                if not persons:
                    empty_queries += 1

                if verbose:
                    print(f"  uuid={res.get('uuid')!r} text={text_value!r} "
                          f"-> {len(persons)} personne(s)")
    finally:
        engine.close()

    end = time_module.time()

    print(f"Temps total : {end - start:.2f} secondes")
    print(f"Temps moyen / mention : {(end - start) / max(len(mentions), 1):.4f} secondes")
    print(f"Resultats retournes : {total_results}")
    print(f"Mentions sans resultat : {empty_queries}")

    return tasks


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Lie les mentions PER/SPK d'un export Label Studio pre-traite via DECIDON."
    )
    parser.add_argument("--json", type=str, required=True)
    parser.add_argument("--output-json", type=str, required=True)
    parser.add_argument("--bool-type", type=str, choices=["AND", "OR"], default="AND")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args()

    output = run_pretraite_scaled(
        filename=args.json,
        bool_type=args.bool_type,
        limit=args.limit,
        verbose=args.verbose,
    )

    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Resultats JSON ecrits dans : {args.output_json}")


if __name__ == "__main__":
    main()