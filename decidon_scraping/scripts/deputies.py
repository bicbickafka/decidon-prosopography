"""Scrape deputies of the French Third Republic from Sycomore.

Source: https://www2.assemblee-nationale.fr/sycomore/liste/{i} for i in range(26, 43)

Options:
    --limit N      Process only the first N records (for testing).
    --output FILE  Path of the output CSV file.

Example:
python deputies.py \
    https://www2.assemblee-nationale.fr/sycomore/liste/26 \
    --limit 5 \
    --output deputies_test.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import time
import unicodedata
from dataclasses import dataclass
from typing import Iterable, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://www2.assemblee-nationale.fr"

DEFAULT_LIST_URLS = [
    f"https://www2.assemblee-nationale.fr/sycomore/liste/{i}"
    for i in range(26, 43)
]

WIKIDATA_API_URL = "https://www.wikidata.org/w/api.php"
SPARQL_URL = "https://query.wikidata.org/sparql"
USER_AGENT = "deputes-scraper/1.0 (research script; contact your-email@example.org)"
HEADERS = {"User-Agent": USER_AGENT}
WHITESPACE_RE = re.compile(r"\s+")

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
    "https://www2.assemblee-nationale.fr/sycomore/liste/26": {
        "name": "Assemblée nationale",
        "start": "1871-02-12",
        "end": "1876-03-07",
        "qid": "Q9516798",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/Assembl%C3%A9e_nationale_(1871)",
    },
    "https://www2.assemblee-nationale.fr/sycomore/liste/27": {
        "name": "Ire législature de la Troisième République",
        "start": "1876-03-08",
        "end": "1877-06-25",
        "qid": "Q33754196",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/Ire_l%C3%A9gislature_de_la_Troisième_R%C3%A9publique_fran%C3%A7aise",
    },
    "https://www2.assemblee-nationale.fr/sycomore/liste/28": {
        "name": "IIe législature de la Troisième République",
        "start": "1877-11-07",
        "end": "1881-10-27",
        "qid": "Q33757119",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/IIe_l%C3%A9gislature_de_la_Troisième_R%C3%A9publique_fran%C3%A7aise",
    },
    "https://www2.assemblee-nationale.fr/sycomore/liste/29": {
        "name": "IIIe législature de la Troisième République",
        "start": "1881-10-28",
        "end": "1885-11-09",
        "qid": "Q33756706",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/IIIe_l%C3%A9gislature_de_la_Troisième_R%C3%A9publique_fran%C3%A7aise",
    },
    "https://www2.assemblee-nationale.fr/sycomore/liste/30": {
        "name": "IVe législature de la Troisième République",
        "start": "1885-11-10",
        "end": "1889-11-11",
        "qid": "Q33756209",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/IVe_l%C3%A9gislature_de_la_Troisième_R%C3%A9publique_fran%C3%A7aise",
    },
    "https://www2.assemblee-nationale.fr/sycomore/liste/31": {
        "name": "Ve législature de la Troisième République",
        "start": "1889-11-12",
        "end": "1893-10-14",
        "qid": "Q33755832",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/Ve_l%C3%A9gislature_de_la_Troisième_R%C3%A9publique_fran%C3%A7aise",
    },
    "https://www2.assemblee-nationale.fr/sycomore/liste/32": {
        "name": "VIe législature de la Troisième République",
        "start": "1893-10-15",
        "end": "1898-05-31",
        "qid": "Q33755445",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/VIe_l%C3%A9gislature_de_la_Troisième_R%C3%A9publique_fran%C3%A7aise",
    },
    "https://www2.assemblee-nationale.fr/sycomore/liste/33": {
        "name": "VIIe législature de la Troisième République",
        "start": "1898-06-01",
        "end": "1902-05-31",
        "qid": "Q33322771",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/VIIe_l%C3%A9gislature_de_la_Troisième_R%C3%A9publique_fran%C3%A7aise",
    },
    "https://www2.assemblee-nationale.fr/sycomore/liste/34": {
        "name": "VIIIe législature de la Troisième République",
        "start": "1902-06-01",
        "end": "1906-05-31",
        "qid": "Q33323082",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/VIIIe_l%C3%A9gislature_de_la_Troisième_R%C3%A9publique_fran%C3%A7aise",
    },
    "https://www2.assemblee-nationale.fr/sycomore/liste/35": {
        "name": "IXe législature de la Troisième République",
        "start": "1906-06-01",
        "end": "1910-05-31",
        "qid": "Q33323183",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/IXe_l%C3%A9gislature_de_la_Troisième_R%C3%A9publique_fran%C3%A7aise",
    },
    "https://www2.assemblee-nationale.fr/sycomore/liste/36": {
        "name": "Xe législature de la Troisième République",
        "start": "1910-06-01",
        "end": "1914-05-31",
        "qid": "Q33369535",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/Xe_l%C3%A9gislature_de_la_Troisième_R%C3%A9publique_fran%C3%A7aise",
    },
    "https://www2.assemblee-nationale.fr/sycomore/liste/37": {
        "name": "XIe législature de la Troisième République",
        "start": "1914-06-01",
        "end": "1919-12-07",
        "qid": "Q33528422",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/XIe_l%C3%A9gislature_de_la_Troisième_R%C3%A9publique_fran%C3%A7aise",
    },
    "https://www2.assemblee-nationale.fr/sycomore/liste/38": {
        "name": "XIIe législature de la Troisième République",
        "start": "1919-12-08",
        "end": "1924-05-31",
        "qid": "Q33724121",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/XIIe_l%C3%A9gislature_de_la_Troisième_R%C3%A9publique_fran%C3%A7aise",
    },
    "https://www2.assemblee-nationale.fr/sycomore/liste/39": {
        "name": "XIIIe législature de la Troisième République",
        "start": "1924-06-01",
        "end": "1928-05-31",
        "qid": "Q16683492",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/XIIIe_l%C3%A9gislature_de_la_Troisième_R%C3%A9publique_fran%C3%A7aise",
    },
    "https://www2.assemblee-nationale.fr/sycomore/liste/40": {
        "name": "XIVe législature de la Troisième République",
        "start": "1928-06-01",
        "end": "1932-05-31",
        "qid": "Q33728280",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/XIVe_l%C3%A9gislature_de_la_Troisième_R%C3%A9publique_fran%C3%A7aise",
    },
    "https://www2.assemblee-nationale.fr/sycomore/liste/41": {
        "name": "XVe législature de la Troisième République",
        "start": "1932-06-01",
        "end": "1936-05-31",
        "qid": "Q16683508",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/XVe_l%C3%A9gislature_de_la_Troisième_R%C3%A9publique_fran%C3%A7aise",
    },
    "https://www2.assemblee-nationale.fr/sycomore/liste/42": {
        "name": "XVIe législature de la Troisième République",
        "start": "1936-06-01",
        "end": "1942-05-31",
        "qid": "Q16683505",
        "wikipedia_url": "https://fr.wikipedia.org/wiki/XVIe_l%C3%A9gislature_de_la_Troisième_R%C3%A9publique_fran%C3%A7aise",
    },
}

LIST_FILTERS_RAW = {
    "https://www2.assemblee-nationale.fr/sycomore/liste/26": {
        "regimes": {"Assemblée Nationale"},
        "legislatures": set(),
    },
    "https://www2.assemblee-nationale.fr/sycomore/liste/27": {
        "regimes": {"Troisième République - Chambre des députés"},
        "legislatures": {"Ire législature"},
    },
    "https://www2.assemblee-nationale.fr/sycomore/liste/28": {
        "regimes": {"Troisième République - Chambre des députés"},
        "legislatures": {"IIe législature"},
    },
    "https://www2.assemblee-nationale.fr/sycomore/liste/29": {
        "regimes": {"Troisième République - Chambre des députés"},
        "legislatures": {"IIIe législature"},
    },
    "https://www2.assemblee-nationale.fr/sycomore/liste/30": {
        "regimes": {"Troisième République - Chambre des députés"},
        "legislatures": {"IVe législature"},
    },
    "https://www2.assemblee-nationale.fr/sycomore/liste/31": {
        "regimes": {"Troisième République - Chambre des députés"},
        "legislatures": {"Ve législature"},
    },
    "https://www2.assemblee-nationale.fr/sycomore/liste/32": {
        "regimes": {"Troisième République - Chambre des députés"},
        "legislatures": {"VIe législature"},
    },
    "https://www2.assemblee-nationale.fr/sycomore/liste/33": {
        "regimes": {"Troisième République - Chambre des députés"},
        "legislatures": {"VIIe législature"},
    },
    "https://www2.assemblee-nationale.fr/sycomore/liste/34": {
        "regimes": {"Troisième République - Chambre des députés"},
        "legislatures": {"VIIIe législature"},
    },
    "https://www2.assemblee-nationale.fr/sycomore/liste/35": {
        "regimes": {"Troisième République - Chambre des députés"},
        "legislatures": {"IXe législature"},
    },
    "https://www2.assemblee-nationale.fr/sycomore/liste/36": {
        "regimes": {"Troisième République - Chambre des députés"},
        "legislatures": {"Xe législature"},
    },
    "https://www2.assemblee-nationale.fr/sycomore/liste/37": {
        "regimes": {"Troisième République - Chambre des députés"},
        "legislatures": {"XIe législature"},
    },
    "https://www2.assemblee-nationale.fr/sycomore/liste/38": {
        "regimes": {"Troisième République - Chambre des députés"},
        "legislatures": {"XIIe législature"},
    },
    "https://www2.assemblee-nationale.fr/sycomore/liste/39": {
        "regimes": {"Troisième République - Chambre des députés"},
        "legislatures": {"XIIIe législature"},
    },
    "https://www2.assemblee-nationale.fr/sycomore/liste/40": {
        "regimes": {"Troisième République - Chambre des députés"},
        "legislatures": {"XIVe législature"},
    },
    "https://www2.assemblee-nationale.fr/sycomore/liste/41": {
        "regimes": {"Troisième République - Chambre des députés"},
        "legislatures": {"XVe législature"},
    },
    "https://www2.assemblee-nationale.fr/sycomore/liste/42": {
        "regimes": {"Troisième République - Chambre des députés"},
        "legislatures": {"XVIe législature"},
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
    person__sycomore_id: str | None
    person__wikidata_qid: str | None
    person__wikipedia_url: str | None


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)

    retry = Retry(
        total=5,
        connect=5,
        read=5,
        status=5,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET"]),
        respect_retry_after_header=True,
    )

    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def normalize_space(text: str | None) -> str:
    if not text:
        return ""
    return WHITESPACE_RE.sub(" ", str(text).replace("\xa0", " ")).strip()


def strip_accents(text: str | None) -> str:
    if not text:
        return ""
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def normalize_label(text: str | None) -> str:
    s = normalize_space(text)
    s = strip_accents(s).lower()
    s = s.replace("1re", "ire")
    s = s.replace("1ere", "ire")
    s = s.replace("1ère", "ire")
    s = s.replace("1er", "i")
    s = s.replace("ieme", "e")
    s = s.replace("ème", "e")
    s = s.replace("ere", "re")
    s = s.replace("'", " ")
    s = s.replace("’", " ")
    s = re.sub(r"[\(\)\[\],.;:]", " ", s)
    s = re.sub(r"\s*-\s*", " - ", s)
    s = WHITESPACE_RE.sub(" ", s).strip()
    return s


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
    if not full_name or "dit" not in full_name.lower():
        return None
    m = re.search(r",\s*dit\s+(.+)$", full_name, re.IGNORECASE)
    if not m:
        m = re.search(r"\bdit\b\s+(.+)$", full_name, re.IGNORECASE)
    if not m:
        return None
    return normalize_person_name_case(m.group(1).strip(" ,"))


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


def extract_precise(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        res = match.group(1).strip()
        res = re.split(r"(?:Département|à|Mandats|Profession)", res)[0].strip()
        return res
    return None


def extract_birth_death(text: str) -> tuple[str | None, str | None]:
    birth_raw = extract_precise(
        r"Né(?:e)? le ([\d\w\séûôîàùç\-]+?)(?=\s*(?:à|Décédé|Mandats|Profession|$))",
        text,
    )
    death_raw = extract_precise(
        r"Décédé(?:e)? le ([\d\w\séûôîàùç\-]+?)(?=\s*(?:à|Mandats|Profession|$))",
        text,
    )
    return parse_french_date_to_iso(birth_raw), parse_french_date_to_iso(death_raw)


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def sparql_query(session: requests.Session, query: str):
    resp = session.get(
        SPARQL_URL,
        params={"query": query, "format": "json"},
        headers=HEADERS,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["results"]["bindings"]


def sycomore_ids_to_qids(session: requests.Session, sycomore_ids: list[str]) -> dict[str, str]:
    clean_ids = sorted({str(int(float(x))) for x in sycomore_ids if str(x).strip()})
    out = {}
    for batch in chunks(clean_ids, 200):
        values = " ".join(f'"{sid}"' for sid in batch)
        query = f"""
SELECT ?item ?sid WHERE {{
  VALUES ?sid {{ {values} }}
  ?item wdt:P1045 ?sid.
}}"""
        rows = sparql_query(session, query)
        for r in rows:
            sid = r["sid"]["value"]
            qid = r["item"]["value"].split("/")[-1]
            out[sid] = qid
        time.sleep(1)
    return out


def split_french_person_name(full_name: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    if not full_name:
        return None, None

    tokens = normalize_space(full_name).split()
    particles = {"de", "du", "des", "d'", "le", "la"}
    filtered = [t for t in tokens if t.lower() not in {"m.", "mr", "mme", "madame"}]
    tokens = filtered or tokens

    if len(tokens) == 1:
        return tokens[0], None
    if len(tokens) == 2:
        return tokens[1], tokens[0]

    last_tokens = [tokens[-1]]
    i = len(tokens) - 2
    while i >= 0 and tokens[i].lower() in particles:
        last_tokens.insert(0, tokens[i])
        i -= 1

    first_tokens = tokens[: i + 1]
    if not first_tokens:
        return full_name, None

    return " ".join(last_tokens), " ".join(first_tokens)


def split_wikidata_label(label: str | None) -> tuple[str | None, str | None]:
    if not label:
        return None, None
    label = normalize_space(label)
    if "," in label:
        last, first = [x.strip() for x in label.split(",", 1)]
        return last or None, first or None
    return split_french_person_name(label)


def wikidata_qids_to_person_info(
    session: requests.Session,
    qids: list[str],
    batch_size: int = 50,
) -> dict[str, dict[str, str | None]]:
    qid_map = {
        qid: {
            "birth_date": None,
            "death_date": None,
            "wikipedia_url": None,
            "label_fr": None,
            "first_name": None,
            "last_name": None,
        }
        for qid in qids if qid
    }

    unique_qids = list(qid_map.keys())

    for batch in chunks(unique_qids, batch_size):
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
            timeout=30,
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

        time.sleep(0.2)

    return qid_map


def fetch_list_member_urls(session: requests.Session, list_url: str) -> list[str]:
    if "alpha=" not in list_url:
        separator = "&" if "?" in list_url else "?"
        list_url = f"{list_url}{separator}alpha=true"

    resp = session.get(list_url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")

    urls = []
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if "/sycomore/fiche/" in href:
            urls.append(urljoin(BASE_URL, href))

    return list(dict.fromkeys(urls))


def infer_legislature_from_url(list_url: str) -> dict | None:
    return MANDATES.get(list_url)


def build_normalized_filters() -> dict[str, dict[str, set[str]]]:
    out = {}
    for list_url, raw in LIST_FILTERS_RAW.items():
        out[list_url] = {
            "regimes": {normalize_label(x) for x in raw.get("regimes", set()) if x},
            "legislatures": {normalize_label(x) for x in raw.get("legislatures", set()) if x},
        }
    return out


LIST_FILTERS = build_normalized_filters()


def get_list_filter(list_url: str) -> dict[str, set[str]]:
    return LIST_FILTERS.get(list_url, {"regimes": set(), "legislatures": set()})


def extract_dt_dd_map(block: BeautifulSoup) -> dict[str, str]:
    pairs = {}
    dts = block.find_all("dt")
    dds = block.find_all("dd")
    for dt, dd in zip(dts, dds):
        dt_text = normalize_space(dt.get_text(" ", strip=True))
        dd_text = normalize_space(dd.get_text(" ", strip=True))
        if dt_text:
            pairs[dt_text] = dd_text
    return pairs


def matches_list_filter(
    regime_raw: str | None,
    legislature_raw: str | None,
    list_filter: dict[str, set[str]] | None,
) -> bool:
    if not list_filter:
        return True

    allowed_regimes = list_filter.get("regimes", set())
    allowed_legislatures = list_filter.get("legislatures", set())

    regime = normalize_label(regime_raw)
    legislature = normalize_label(legislature_raw)

    # Case 1: Third Republic legislature pages
    # We require the exact expected legislature.
    if allowed_legislatures:
        if legislature not in allowed_legislatures:
            return False
        if allowed_regimes and regime and regime not in allowed_regimes:
            return False
        return True

    # Case 2: list 26 / Assemblée nationale
    if allowed_regimes:
        return regime in allowed_regimes

    return True


def parse_mandate_blocks(
    soup: BeautifulSoup,
    list_filter: dict[str, set[str]] | None = None,
) -> list[dict]:
    mandates = []
    blocks = soup.find_all("dl")

    for block in blocks:
        text = normalize_space(block.get_text(" ", strip=True))
        if "Mandat" not in text and "Régime politique" not in text:
            continue

        date_range = re.search(
            r"Du ([\d\w\séûôîàùç\-]+?) au ([\d\w\séûôîàùç\-]+)",
            text,
            re.IGNORECASE,
        )
        if not date_range:
            continue

        pairs = extract_dt_dd_map(block)

        regime = None
        legislature = None
        group_value = None

        for k, v in pairs.items():
            nk = normalize_label(k)
            if "regime politique" in nk:
                regime = v
            elif "legislature" in nk:
                legislature = v
            elif "groupe" in nk:
                group_value = v

        if not matches_list_filter(regime, legislature, list_filter):
            continue

        from_raw = normalize_space(date_range.group(1))
        to_raw = normalize_space(re.split(r"Département", date_range.group(2))[0])

        dept_match = re.search(r"Département\s*(.*)", text, re.IGNORECASE)
        constituency_clean = normalize_space(dept_match.group(1)) if dept_match else None
        if constituency_clean:
            constituency_clean = re.split(
                r"(?:Législature|Mandat|Régime politique|Groupe)",
                constituency_clean,
            )[0].strip()

        mandates.append({
            "regime": regime,
            "legislature": legislature,
            "constituency": constituency_clean,
            "group": group_value,
            "start_date": parse_french_date_to_iso(from_raw),
            "end_date": parse_french_date_to_iso(to_raw),
        })

    return mandates


def scrape_depute_fiche(
    session: requests.Session,
    url: str,
    mandate_info: dict | None,
    list_filter: dict[str, set[str]] | None,
    sycomore_qid_map: dict[str, str],
    qid_info: dict[str, dict[str, str | None]],
) -> list[OutputRow]:
    resp = session.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")

    h1 = soup.find("h1")
    if not h1:
        return []

    full_name = normalize_space(h1.get_text(" ", strip=True))
    alias = extract_alias_from_title(full_name)
    base_name = re.sub(r",\s*dit\s+.+$", "", full_name, flags=re.IGNORECASE).strip()
    base_name = re.sub(r"\bdit\b.+$", "", base_name, flags=re.IGNORECASE).strip(" ,")
    last_name, first_name = split_french_person_name(base_name)

    all_text = soup.get_text(" ", strip=True)
    birth_date, death_date = extract_birth_death(all_text)

    syco_match = re.search(r"/fiche/(\d+)", url)
    sycomore_id = syco_match.group(1) if syco_match else None

    qid = None
    wikipedia_url = None

    if sycomore_id:
        qid = sycomore_qid_map.get(sycomore_id)

    if qid:
        wd = qid_info.get(qid, {})
        birth_date = birth_date or wd.get("birth_date")
        death_date = death_date or wd.get("death_date")
        wikipedia_url = wd.get("wikipedia_url")
        first_name = wd.get("first_name") or first_name
        last_name = wd.get("last_name") or last_name

    parsed_mandates = parse_mandate_blocks(soup, list_filter=list_filter)
    if not parsed_mandates:
        return []

    rows = []
    for pm in parsed_mandates:
        rows.append(
            OutputRow(
                mandate__name=mandate_info.get("name") if mandate_info else None,
                mandate__start_date=mandate_info.get("start") if mandate_info else None,
                mandate__end_date=mandate_info.get("end") if mandate_info else None,
                mandate__wikipedia_qid=mandate_info.get("qid") if mandate_info else None,
                mandate__wikipedia_url=mandate_info.get("wikipedia_url") if mandate_info else None,
                person_mandate__constituency=pm.get("constituency"),
                person_mandate__group=pm.get("group"),
                person_mandate__start_date=pm.get("start_date"),
                person_mandate__end_date=pm.get("end_date"),
                person__last_name=last_name,
                person__first_name=first_name,
                person__alias=alias,
                person__birth_date=birth_date,
                person__death_date=death_date,
                person__sycomore_id=sycomore_id,
                person__wikidata_qid=qid,
                person__wikipedia_url=wikipedia_url,
            )
        )

    return rows


def write_csv(rows: Iterable[OutputRow], output_path: str) -> None:
    fieldnames = [
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
        "person__sycomore_id",
        "person__wikidata_qid",
        "person__wikipedia_url",
    ]

    with open(output_path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract députés from Assemblée nationale Sycomore lists."
    )
    parser.add_argument(
        "list_urls",
        nargs="*",
        default=DEFAULT_LIST_URLS,
        help="One or more Sycomore list URLs",
    )
    parser.add_argument("--output", default="deputes.csv", help="Output CSV path")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of deputies per list URL")
    args = parser.parse_args()

    session = build_session()

    member_contexts: list[tuple[str, dict | None, dict[str, set[str]]]] = []
    all_member_urls: list[str] = []

    for list_url in args.list_urls:
        urls = fetch_list_member_urls(session, list_url)
        if args.limit is not None:
            urls = urls[:args.limit]

        mandate_info = infer_legislature_from_url(list_url)
        list_filter = get_list_filter(list_url)

        for member_url in urls:
            member_contexts.append((member_url, mandate_info, list_filter))
            all_member_urls.append(member_url)

    sycomore_ids = []
    for member_url in all_member_urls:
        m = re.search(r"/fiche/(\d+)", member_url)
        if m:
            sycomore_ids.append(m.group(1))

    sycomore_qid_map = sycomore_ids_to_qids(session, sycomore_ids)
    qid_info = wikidata_qids_to_person_info(session, list(sycomore_qid_map.values()))

    rows = []
    seen = set()

    for member_url, mandate_info, list_filter in member_contexts:
        key = (
            member_url,
            mandate_info.get("name") if mandate_info else None,
        )
        if key in seen:
            continue
        seen.add(key)

        try:
            member_rows = scrape_depute_fiche(
                session,
                member_url,
                mandate_info,
                list_filter,
                sycomore_qid_map,
                qid_info,
            )
            rows.extend(member_rows)
        except requests.RequestException as e:
            print(f"[WARN] fiche ignorée après retries: {member_url} -> {e}")
            time.sleep(0.5)

    write_csv(rows, args.output)


if __name__ == "__main__":
    main()