"""Scrape senators of the French Third Republic from the Sénat website.

Source: https://www.senat.fr/senateurs-3eme-republique/senatl.html

Options:
    --name-filter TEXT  Process only senators whose name contains TEXT.
    --limit N           Process only the first N records (for testing).
    --resume            Continue from an existing output file instead of restarting.
    --output FILE       Path of the output CSV file.

Examples:
python senators.py \
    --name-filter aguillon \
    --output senators_aguillon.csv
python senators.py \
    --limit 5 \
    --output senators_test.csv
python senators.py \
    --resume \
    --output senators.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://www.senat.fr"
INDEX_URL = "https://www.senat.fr/senateurs-3eme-republique/senatl.html"
WIKIDATA_API_URL = "https://www.wikidata.org/w/api.php"
SPARQL_URL = "https://query.wikidata.org/sparql"
USER_AGENT = "senateurs-scraper/1.1 (historical-parliament-db)"
HEADERS = {"User-Agent": USER_AGENT}
WHITESPACE_RE = re.compile(r"\s+")

CSV_FIELDNAMES = [
    "mandate__name",
    "mandate__start_date",
    "mandate__end_date",
    "mandate__wikipedia_qid",
    "mandate__wikipedia_url",
    "person_mandate__constituency",
    "person_mandate__group",
    "person_mandate__start_date",
    "person_mandate__end_date",
    "person__last_name",
    "person__first_name",
    "person__alias",
    "person__birth_date",
    "person__death_date",
    "person__senat_id",
    "person__wikidata_qid",
    "person__wikipedia_url",
]

MONTHS_FR = {
    "janvier": "01",
    "février": "02",
    "fevrier": "02",
    "mars": "03",
    "avril": "04",
    "mai": "05",
    "juin": "06",
    "juillet": "07",
    "août": "08",
    "aout": "08",
    "septembre": "09",
    "octobre": "10",
    "novembre": "11",
    "décembre": "12",
    "decembre": "12",
}

MANDATES = {
    "Élections sénatoriales de 1876": {
        "name": "Élections sénatoriales de 1876",
        "start": "1876-01-27",
        "end": "1879-01-04",
        "qid": "Q97178405",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/%C3%89lections_s%C3%A9natoriales_fran%C3%A7aises_de_1876",
    },
    "Élections sénatoriales de 1879": {
        "name": "Élections sénatoriales de 1879",
        "start": "1879-01-05",
        "end": "1882-01-07",
        "qid": "Q97183536",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/%C3%89lections_s%C3%A9natoriales_fran%C3%A7aises_de_1879",
    },
    "Élections sénatoriales de 1882": {
        "name": "Élections sénatoriales de 1882",
        "start": "1882-01-08",
        "end": "1885-01-24",
        "qid": "Q111103097",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/%C3%89lections_s%C3%A9natoriales_fran%C3%A7aises_de_1882",
    },
    "Élections sénatoriales de 1885": {
        "name": "Élections sénatoriales de 1885",
        "start": "1885-01-25",
        "end": "1888-01-04",
        "qid": "Q56306075",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/%C3%89lections_s%C3%A9natoriales_fran%C3%A7aises_de_1885",
    },
    "Élections sénatoriales de 1888": {
        "name": "Élections sénatoriales de 1888",
        "start": "1888-01-05",
        "end": "1891-01-03",
        "qid": "Q111103098",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/%C3%89lections_s%C3%A9natoriales_fran%C3%A7aises_de_1888",
    },
    "Élections sénatoriales de 1891": {
        "name": "Élections sénatoriales de 1891",
        "start": "1891-01-04",
        "end": "1894-01-06",
        "qid": "Q111103099",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/%C3%89lections_s%C3%A9natoriales_fran%C3%A7aises_de_1891",
    },
    "Élections sénatoriales de 1894": {
        "name": "Élections sénatoriales de 1894",
        "start": "1894-01-07",
        "end": "1897-01-02",
        "qid": "Q67945020",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/%C3%89lections_s%C3%A9natoriales_fran%C3%A7aises_de_1894",
    },
    "Élections sénatoriales de 1897": {
        "name": "Élections sénatoriales de 1897",
        "start": "1897-01-03",
        "end": "1900-01-31",
        "qid": "Q67944206",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/%C3%89lections_s%C3%A9natoriales_fran%C3%A7aises_de_1897",
    },
    "Élections sénatoriales de 1900": {
        "name": "Élections sénatoriales de 1900",
        "start": "1900-02-01",
        "end": "1903-01-03",
        "qid": "Q28496159",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/%C3%89lections_s%C3%A9natoriales_fran%C3%A7aises_de_1900",
    },
    "Élections sénatoriales de 1903": {
        "name": "Élections sénatoriales de 1903",
        "start": "1903-01-04",
        "end": "1906-01-06",
        "qid": "Q35203776",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/%C3%89lections_s%C3%A9natoriales_fran%C3%A7aises_de_1903",
    },
    "Élections sénatoriales de 1906": {
        "name": "Élections sénatoriales de 1906",
        "start": "1906-01-07",
        "end": "1909-01-02",
        "qid": "Q111103101",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/%C3%89lections_s%C3%A9natoriales_fran%C3%A7aises_de_1906",
    },
    "Élections sénatoriales de 1909": {
        "name": "Élections sénatoriales de 1909",
        "start": "1909-01-03",
        "end": "1912-01-06",
        "qid": "Q111103102",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/%C3%89lections_s%C3%A9natoriales_fran%C3%A7aises_de_1909",
    },
    "Élections sénatoriales de 1912": {
        "name": "Élections sénatoriales de 1912",
        "start": "1912-01-07",
        "end": "1920-01-10",
        "qid": "Q36713863",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/%C3%89lections_s%C3%A9natoriales_fran%C3%A7aises_de_1912",
    },
    "Élections sénatoriales de 1920": {
        "name": "Élections sénatoriales de 1920",
        "start": "1920-01-11",
        "end": "1921-01-08",
        "qid": "Q111103103",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/%C3%89lections_s%C3%A9natoriales_fran%C3%A7aises_de_1920",
    },
    "Élections sénatoriales de 1921": {
        "name": "Élections sénatoriales de 1921",
        "start": "1921-01-09",
        "end": "1924-01-05",
        "qid": "Q28494844",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/%C3%89lections_s%C3%A9natoriales_fran%C3%A7aises_de_1921",
    },
    "Élections sénatoriales de 1924": {
        "name": "Élections sénatoriales de 1924",
        "start": "1924-01-06",
        "end": "1927-01-08",
        "qid": "Q28494840",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/%C3%89lections_s%C3%A9natoriales_fran%C3%A7aises_de_1924",
    },
    "Élections sénatoriales de 1927": {
        "name": "Élections sénatoriales de 1927",
        "start": "1927-01-09",
        "end": "1929-10-19",
        "qid": "Q28494841",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/%C3%89lections_s%C3%A9natoriales_fran%C3%A7aises_de_1927",
    },
    "Élections sénatoriales de 1929": {
        "name": "Élections sénatoriales de 1929",
        "start": "1929-10-20",
        "end": "1932-10-15",
        "qid": "Q28494842",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/%C3%89lections_s%C3%A9natoriales_fran%C3%A7aises_de_1929",
    },
    "Élections sénatoriales de 1932": {
        "name": "Élections sénatoriales de 1932",
        "start": "1932-10-16",
        "end": "1935-10-19",
        "qid": "Q28494845",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/%C3%89lections_s%C3%A9natoriales_fran%C3%A7aises_de_1932",
    },
    "Élections sénatoriales de 1935": {
        "name": "Élections sénatoriales de 1935",
        "start": "1935-10-20",
        "end": "1938-10-22",
        "qid": "Q28494839",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/%C3%89lections_s%C3%A9natoriales_fran%C3%A7aises_de_1935",
    },
    "Élections sénatoriales de 1938": {
        "name": "Élections sénatoriales de 1938",
        "start": "1938-10-23",
        "end": "1940-07-10",
        "qid": "Q28494838",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/%C3%89lections_s%C3%A9natoriales_fran%C3%A7aises_de_1938",
    },
    "Sénateur inamovible": {
        "name": "Sénateur inamovible",
        "start": "1875-02-24",
        "end": "1884-12-09",
        "qid": "Q3510904",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/S%C3%A9nateur_inamovible",
    },
}


@dataclass
class OutputRow:
    mandate__name: str | None
    mandate__start_date: str | None
    mandate__end_date: str | None
    mandate__wikipedia_qid: str | None
    mandate__wikipedia_url: str | None
    person_mandate__constituency: str | None
    person_mandate__group: str | None
    person_mandate__start_date: str | None
    person_mandate__end_date: str | None
    person__last_name: str | None
    person__first_name: str | None
    person__alias: str | None
    person__birth_date: str | None
    person__death_date: str | None
    person__senat_id: str | None
    person__wikidata_qid: str | None
    person__wikipedia_url: str | None


def normalize_space(text: str | None) -> str:
    if not text:
        return ""
    return WHITESPACE_RE.sub(" ", str(text).replace("\xa0", " ")).strip()


def clean_date(date_str: str | None) -> str | None:
    if not date_str:
        return None
    return re.sub(r"\(.*?\)", "", date_str).strip()


def is_in_period(date_str: str | None, start_year: int = 1875, end_year: int = 1945) -> bool:
    if not date_str:
        return False
    year_match = re.search(r"\d{4}", date_str)
    if year_match:
        year = int(year_match.group(0))
        return start_year <= year <= end_year
    return False


def quick_find(pattern: str, text: str) -> str | None:
    m = re.search(pattern, text, re.IGNORECASE)
    return normalize_space(m.group(1)) if m else None


def parse_french_date_to_iso(text: str | None) -> str | None:
    if not text:
        return None
    s = normalize_space(text.lower())
    s = s.replace("1er", "1").replace("’", "'").replace("'", " ")
    s = normalize_space(s)
    m = re.search(r"(\d{1,2})\s+([a-zéûôîàùç-]+)\s+(\d{4})", s)
    if not m:
        return None
    day, month_fr, year = m.groups()
    month = MONTHS_FR.get(month_fr)
    if not month:
        return None
    return f"{year}-{month}-{int(day):02d}"


def minus_one_day(iso_date: str | None) -> str | None:
    if not iso_date:
        return None
    dt = datetime.strptime(iso_date, "%Y-%m-%d").date()
    return (dt - timedelta(days=1)).isoformat()


def normalize_person_name_case(text: str | None) -> str | None:
    if not text:
        return None
    parts = normalize_space(text).split()
    out = []
    for part in parts:
        if "-" in part:
            out.append("-".join(p.capitalize() if p else p for p in part.split("-")))
        else:
            out.append(part.capitalize())
    return " ".join(out)


def extract_alias_from_title(full_name: str | None) -> str | None:
    if not full_name or " dit " not in full_name.lower():
        return None
    m = re.search(r"\bdit\b\s+(.+)$", full_name, re.IGNORECASE)
    if not m:
        return None
    return normalize_person_name_case(m.group(1).strip())


def split_senator_name(full_name: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    if not full_name:
        return None, None
    tokens = normalize_space(full_name).split()
    particles = {"de", "du", "des", "d'", "le", "la"}
    filtered = [t for t in tokens if t.lower() not in {"m.", "mr", "mme", "madame"}]
    tokens = filtered or tokens
    if len(tokens) == 1:
        return tokens[0], None
    if len(tokens) == 2:
        return tokens[0], tokens[1]
    first_tokens = [tokens[-1]]
    last_tokens = tokens[:-1]
    if len(last_tokens) >= 2 and last_tokens[-1].lower() in particles:
        first_tokens.insert(0, last_tokens.pop())
    return " ".join(last_tokens), " ".join(first_tokens)


def split_wikidata_label(label: str | None) -> tuple[str | None, str | None]:
    if not label:
        return None, None
    label = normalize_space(label)
    if "," in label:
        last, first = [x.strip() for x in label.split(",", 1)]
        return last or None, first or None
    return split_senator_name(label)


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)

    retry = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def json_load(path: Path, default):
    if path.exists():
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return default


def json_dump(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    tmp.replace(path)


def sparql_query(session: requests.Session, query: str):
    resp = session.get(
        SPARQL_URL,
        params={"query": query, "format": "json"},
        headers=HEADERS,
        timeout=(10, 60),
    )
    resp.raise_for_status()
    return resp.json()["results"]["bindings"]


def get_core_name(sid: str | None) -> str | None:
    if not sid:
        return None
    return re.sub(r"\d+r\d+$", "", str(sid)).strip()


def senat_ids_to_qids(
    session: requests.Session,
    senat_ids: list[str],
    cache_path: Path | None = None,
) -> dict[str, str]:
    cached = json_load(cache_path, {}) if cache_path else {}

    senat_raw_ids = sorted({sid for sid in senat_ids if sid})
    senat_core_map = {get_core_name(sid): sid for sid in senat_raw_ids if get_core_name(sid)}
    core_names = list(senat_core_map.keys())

    senat_map = dict(cached)
    missing_core_names = [
        core for core in core_names
        if senat_core_map.get(core) not in senat_map
    ]

    for batch in chunks(missing_core_names, 50):
        values = " ".join(f'"{name}"' for name in batch)
        query = f"""
SELECT ?item ?sid_found ?core WHERE {{
  VALUES ?core {{ {values} }}
  ?item p:P1808/ps:P1808 ?sid_found .
  FILTER(CONTAINS(?sid_found, ?core))
}}"""
        rows = sparql_query(session, query)
        for r in rows:
            qid = r["item"]["value"].split("/")[-1]
            core_name = r["core"]["value"]
            original_id = senat_core_map.get(core_name)
            if original_id and original_id not in senat_map:
                senat_map[original_id] = qid

        if cache_path:
            json_dump(cache_path, senat_map)
        time.sleep(1)

    return senat_map


def wikidata_qids_to_person_info(
    session: requests.Session,
    qids: list[str],
    batch_size: int = 50,
    cache_path: Path | None = None,
) -> dict[str, dict[str, str | None]]:
    cached = json_load(cache_path, {}) if cache_path else {}

    qid_map = dict(cached)
    unique_qids = sorted({qid for qid in qids if qid})
    missing_qids = [qid for qid in unique_qids if qid not in qid_map]

    for batch in chunks(missing_qids, batch_size):
        resp = session.get(
            WIKIDATA_API_URL,
            params={
                "action": "wbgetentities",
                "format": "json",
                "ids": "|".join(batch),
                "props": "claims|sitelinks|labels",
                "languages": "fr",
            },
            headers=HEADERS,
            timeout=(10, 30),
        )
        resp.raise_for_status()
        entities = resp.json().get("entities", {})

        for qid in batch:
            entity = entities.get(qid, {})
            claims = entity.get("claims", {})

            def extract_date(prop_id: str) -> str | None:
                if prop_id not in claims:
                    return None
                try:
                    date_val = claims[prop_id][0]["mainsnak"]["datavalue"]["value"]["time"]
                    return date_val.lstrip("+").split("T", 1)[0]
                except (IndexError, KeyError, TypeError):
                    return None

            sitelinks = entity.get("sitelinks", {})
            wikipedia_url = None
            if "frwiki" in sitelinks:
                title = sitelinks["frwiki"]["title"].replace(" ", "_")
                wikipedia_url = f"https://fr.wikipedia.org/wiki/{title}"

            label_fr = entity.get("labels", {}).get("fr", {}).get("value")
            last_name, first_name = split_wikidata_label(label_fr)

            qid_map[qid] = {
                "birth_date": extract_date("P569"),
                "death_date": extract_date("P570"),
                "wikipedia_url": wikipedia_url,
                "label_fr": label_fr,
                "first_name": first_name,
                "last_name": last_name,
            }

        if cache_path:
            json_dump(cache_path, qid_map)
        time.sleep(0.2)

    for qid in unique_qids:
        qid_map.setdefault(
            qid,
            {
                "birth_date": None,
                "death_date": None,
                "wikipedia_url": None,
                "label_fr": None,
                "first_name": None,
                "last_name": None,
            },
        )

    return qid_map


def fetch_index_links(session: requests.Session) -> list[str]:
    resp = session.get(INDEX_URL, headers=HEADERS, timeout=(10, 30))
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")

    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "senateur-3eme-republique/" in href and not href.endswith("senatl.html"):
            links.append(urljoin(BASE_URL + "/", href))
    return sorted(dict.fromkeys(links))


def infer_mandate_from_start(start_iso: str | None) -> dict | None:
    if not start_iso:
        return None
    for mandate in MANDATES.values():
        if mandate["start"] <= start_iso <= mandate["end"]:
            return mandate
    return None


def parse_senator_mandates(all_text: str, constituency: str | None) -> list[dict]:
    starts_raw = re.findall(
        r"(?:Elu|Élu|Réélu)\s+(?:le|du)\s+([\d\w\séûôîàùç\-]+?\d{4})(?=\s*(?:au|le|Fin|Décédé|Elu|Élu|Réélu|Profession|\(|\n|$))",
        all_text,
        re.IGNORECASE,
    )

    final_end_raw = quick_find(
        r"Fin\s+de\s+mandat\s+le\s+([\d\w\séûôîàùç\-]+?\d{4})(?=\s*(?:\(|\n|Biographies|Profession|$))",
        all_text,
    )

    starts_iso = []
    for s in starts_raw:
        cleaned = clean_date(s)
        if is_in_period(cleaned):
            iso = parse_french_date_to_iso(cleaned)
            if iso:
                starts_iso.append(iso)

    final_end_iso = parse_french_date_to_iso(clean_date(final_end_raw)) if final_end_raw else None

    mandates = []
    for i, start_iso in enumerate(starts_iso):
        if i < len(starts_iso) - 1:
            end_iso = minus_one_day(starts_iso[i + 1])
        else:
            end_iso = final_end_iso

        mandate_meta = infer_mandate_from_start(start_iso)

        mandates.append({
            "mandate_meta": mandate_meta,
            "constituency": constituency,
            "group": None,
            "start_date": start_iso,
            "end_date": end_iso,
        })

    return mandates


def scrape_senator(
    session: requests.Session,
    url: str,
    senat_qid_map: dict[str, str],
    qid_info: dict[str, dict[str, str | None]],
) -> list[OutputRow]:
    resp = session.get(url, headers=HEADERS, timeout=(10, 30))
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")
    all_text = soup.get_text(" ", strip=True)

    h1 = soup.find("h1")
    if not h1:
        return []

    full_name = normalize_space(h1.get_text(" ", strip=True))
    alias = extract_alias_from_title(full_name)
    base_name = re.sub(r"\bdit\b.+$", "", full_name, flags=re.IGNORECASE).strip()
    last_name, first_name = split_senator_name(base_name)

    constituency = quick_find(
        r"Département\s*:\s*([\w\s\-'’]+?)(?=\s*(?:Ancien|Election|Élection|Elu|Élu|Réélu|$))",
        all_text,
    )

    birth_raw = clean_date(
        quick_find(r"Né\s+le\s+([\d\w\séûôîàùç\-]+?)(?=\s*(?:à|Décédé|Elu|Élu|Profession|$))", all_text)
    )
    death_raw = clean_date(
        quick_find(r"Décédé\s+le\s+([\d\w\séûôîàùç\-]+?)(?=\s*(?:à|Elu|Élu|Fin|Profession|$))", all_text)
    )

    birth_date = parse_french_date_to_iso(birth_raw)
    death_date = parse_french_date_to_iso(death_raw)

    senat_id = url.split("/")[-1].replace(".html", "")
    qid = senat_qid_map.get(senat_id)
    wikipedia_url = None

    if qid:
        wd = qid_info.get(qid, {})
        birth_date = birth_date or wd.get("birth_date")
        death_date = death_date or wd.get("death_date")
        wikipedia_url = wd.get("wikipedia_url")
        first_name = wd.get("first_name") or first_name
        last_name = wd.get("last_name") or last_name

    parsed_mandates = parse_senator_mandates(all_text, constituency)
    if not parsed_mandates:
        parsed_mandates = [{
            "mandate_meta": None,
            "constituency": constituency,
            "group": None,
            "start_date": None,
            "end_date": None,
        }]

    rows = []
    for pm in parsed_mandates:
        meta = pm.get("mandate_meta") or {}
        rows.append(OutputRow(
            mandate__name=meta.get("name"),
            mandate__start_date=meta.get("start"),
            mandate__end_date=meta.get("end"),
            mandate__wikipedia_qid=meta.get("qid"),
            mandate__wikipedia_url=meta.get("wikipedia_url"),
            person_mandate__constituency=pm.get("constituency"),
            person_mandate__group=pm.get("group"),
            person_mandate__start_date=pm.get("start_date"),
            person_mandate__end_date=pm.get("end_date"),
            person__last_name=last_name,
            person__first_name=first_name,
            person__alias=alias,
            person__birth_date=birth_date,
            person__death_date=death_date,
            person__senat_id=senat_id,
            person__wikidata_qid=qid,
            person__wikipedia_url=wikipedia_url,
        ))
    return rows


def ensure_csv_header(output_path: Path) -> None:
    if output_path.exists() and output_path.stat().st_size > 0:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()


def append_rows(output_path: Path, rows: Iterable[OutputRow]) -> None:
    with open(output_path, "a", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDNAMES)
        for row in rows:
            writer.writerow(asdict(row))


def load_done_ids(checkpoint_path: Path) -> set[str]:
    if not checkpoint_path.exists():
        return set()
    with open(checkpoint_path, "r", encoding="utf-8") as fh:
        return {line.strip() for line in fh if line.strip()}


def mark_done(checkpoint_path: Path, senat_id: str) -> None:
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    with open(checkpoint_path, "a", encoding="utf-8") as fh:
        fh.write(senat_id + "\n")


def write_csv(rows: Iterable[OutputRow], output_path: str) -> None:
    with open(output_path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract Third Republic senators from senat.fr.")
    parser.add_argument("--output", default="senateurs.csv", help="Output CSV path")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of senators from the index")
    parser.add_argument("--name-filter", default=None, help="Only keep senators whose URL contains this text")
    parser.add_argument("--resume", action="store_true", help="Resume from previous run using checkpoint and cache files")
    parser.add_argument("--cache-dir", default=".cache_senateurs", help="Directory for JSON caches and checkpoint files")
    args = parser.parse_args()

    output_path = Path(args.output)
    cache_dir = Path(args.cache_dir)
    senat_qid_cache = cache_dir / "senat_qid_map.json"
    qid_info_cache = cache_dir / "qid_info.json"
    checkpoint_path = cache_dir / f"{output_path.stem}.done.txt"

    session = build_session()

    links = fetch_index_links(session)

    if args.name_filter:
        wanted = args.name_filter.lower()
        links = [u for u in links if wanted in u.lower()]

    if args.limit is not None:
        links = links[:args.limit]

    senat_ids = [u.split("/")[-1].replace(".html", "") for u in links]

    senat_qid_map = senat_ids_to_qids(
        session,
        senat_ids,
        cache_path=senat_qid_cache,
    )
    qid_info = wikidata_qids_to_person_info(
        session,
        list(senat_qid_map.values()),
        cache_path=qid_info_cache,
    )

    done_ids = load_done_ids(checkpoint_path) if args.resume else set()
    links_to_process = []
    for link in links:
        senat_id = link.split("/")[-1].replace(".html", "")
        if senat_id not in done_ids:
            links_to_process.append(link)

    ensure_csv_header(output_path)

    total = len(links_to_process)
    for i, link in enumerate(links_to_process, start=1):
        senat_id = link.split("/")[-1].replace(".html", "")
        print(f"[{i}/{total}] {link}")
        try:
            rows = scrape_senator(session, link, senat_qid_map, qid_info)
            append_rows(output_path, rows)
            mark_done(checkpoint_path, senat_id)
        except Exception as e:
            print(f"ERROR on {senat_id}: {e}")
            continue
        time.sleep(0.3)


if __name__ == "__main__":
    main()