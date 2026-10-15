"""Scrape ministers of the French Third Republic from Wikipedia.

Source: https://fr.wikipedia.org/wiki/Liste_des_gouvernements_de_la_France

Options:
    --output FILE  Path of the output CSV file.

Example:
python ministers.py \
    https://fr.wikipedia.org/wiki/Gouvernement_Dufaure_I
    --output ministers_dufaure_1.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import unquote, urlparse

import requests
from bs4 import BeautifulSoup

API_URL = "https://fr.wikipedia.org/w/api.php"
WIKIDATA_API_URL = "https://www.wikidata.org/w/api.php"
USER_AGENT = "composition-scraper/1.0 (research script; contact your-email@example.org)"
HEADERS = {"User-Agent": USER_AGENT}
BASE_WIKIPEDIA_URL = "https://fr.wikipedia.org"

COMPOSITION_LABELS = {"composition"}
WHITESPACE_RE = re.compile(r"\s+")
ROLE_HINTS = ["chef", "vice-président", "ministre", "sous-secrétaire", "secrétaire"]

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
    'https://fr.wikipedia.org/wiki/Gouvernement_Daladier_V': {"start": '1939-09-13', "end": '1940-03-20', "qid": 'Q3112682'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Daladier_IV': {"start": '1939-05-11', "end": '1939-09-13', "qid": 'Q3112681'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Herriot_I': {"start": '1924-06-14', "end": '1925-04-10', "qid": 'Q3112686'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Painlevé_II': {"start": '1925-04-17', "end": '1925-10-27', "qid": 'Q3112353'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Poincaré_II': {"start": '1922-01-15', "end": '1924-03-29', "qid": 'Q3112409'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Clemenceau_II': {"start": '1917-11-16', "end": '1920-01-18', "qid": 'Q3112068'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Millerand_I': {"start": '1920-01-20', "end": '1920-02-18', "qid": 'Q3111853'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Millerand_II': {"start": '1920-02-18', "end": '1920-09-23', "qid": 'Q3111858'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Leygues': {"start": '1920-09-24', "end": '1921-01-07', "qid": 'Q3112069'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Briand_VII': {"start": '1921-01-16', "end": '1922-01-12', "qid": 'Q3111897'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Duclerc': {"start": '1882-08-07', "end": '1883-01-28', "qid": 'Q2242207'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Fallières': {"start": '1883-01-29', "end": '1883-02-17', "qid": 'Q2448325'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Pétain': {"start": '1940-06-16', "end": '1940-07-10', "qid": 'Q3112368'},
    'https://fr.wikipedia.org/wiki/Gouvernement_de_Freycinet_II': {"start": '1882-01-30', "end": '1882-07-29', "qid": 'Q3111970'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Briand_VIII': {"start": '1925-11-28', "end": '1926-03-06', "qid": 'Q3111898'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Briand_IX': {"start": '1926-03-09', "end": '1926-06-15', "qid": 'Q3111902'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Painlevé_III': {"start": '1925-10-29', "end": '1925-11-22', "qid": 'Q3112355'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Briand_X': {"start": '1926-06-23', "end": '1926-07-17', "qid": 'Q3111886'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Tardieu_II': {"start": '1930-03-02', "end": '1930-12-04', "qid": 'Q643087'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Ribot_V': {"start": '1917-03-20', "end": '1917-09-07', "qid": 'Q3111860'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Briand_V': {"start": '1915-10-29', "end": '1916-12-12', "qid": 'Q3111895'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Doumergue_II': {"start": '1934-02-09', "end": '1934-11-08', "qid": 'Q3112056'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Reynaud': {"start": '1940-03-21', "end": '1940-06-16', "qid": 'Q2718814'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Blum_I': {"start": '1936-06-04', "end": '1937-06-21', "qid": 'Q3112253'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Chautemps_III': {"start": '1937-06-23', "end": '1938-01-14', "qid": 'Q659214'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Chautemps_IV': {"start": '1938-01-18', "end": '1938-03-10', "qid": 'Q3111949'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Bouisson': {"start": '1935-06-01', "end": '1935-06-07', "qid": 'Q2095707'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Pierre-Étienne_Flandin': {"start": '1934-11-08', "end": '1935-05-31', "qid": 'Q3112373'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Laval_IV': {"start": '1935-06-07', "end": '1936-01-22', "qid": 'Q3112381'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Blum_II': {"start": '1938-03-13', "end": '1938-04-08', "qid": 'Q3112254'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Sarraut_II': {"start": '1936-01-24', "end": '1936-06-04', "qid": 'Q3111844'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Painlevé_I': {"start": '1917-09-12', "end": '1917-11-13', "qid": 'Q290305'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Brisson_I': {"start": '1885-04-06', "end": '1885-12-29', "qid": 'Q3112111'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Rouvier_I': {"start": '1887-05-31', "end": '1887-12-04', "qid": 'Q3112275'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Floquet': {"start": '1888-04-03', "end": '1889-02-14', "qid": 'Q2044828'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Tirard_I': {"start": '1887-12-11', "end": '1888-03-30', "qid": 'Q3112392'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Ribot_III': {"start": '1895-01-26', "end": '1895-10-28', "qid": 'Q3111856'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Gambetta': {"start": '1881-11-14', "end": '1882-01-26', "qid": 'Q3112258'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Tirard_II': {"start": '1889-02-23', "end": '1890-03-14', "qid": 'Q3086877'},
    'https://fr.wikipedia.org/wiki/Gouvernement_de_Freycinet_III': {"start": '1886-01-09', "end": '1886-12-05', "qid": 'Q3111971'},
    'https://fr.wikipedia.org/wiki/Gouvernement_de_Freycinet_IV': {"start": '1890-03-18', "end": '1892-02-20', "qid": 'Q21427344'},
    'https://fr.wikipedia.org/wiki/Gouvernement_René_Goblet': {"start": '1886-12-11', "end": '1887-05-19', "qid": 'Q2161327'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Loubet': {"start": '1892-02-27', "end": '1892-11-28', "qid": 'Q1837633'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Ribot_I': {"start": '1892-12-06', "end": '1893-01-11', "qid": 'Q3111852'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Waldeck-Rousseau': {"start": '1899-06-22', "end": '1902-06-03', "qid": 'Q2912866'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Briand_I': {"start": '1909-07-24', "end": '1910-11-03', "qid": 'Q3111885'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Clemenceau_I': {"start": '1906-10-25', "end": '1909-07-20', "qid": 'Q3112064'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Rouvier_II': {"start": '1905-01-24', "end": '1906-02-18', "qid": 'Q1720263'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Rouvier_III': {"start": '1906-02-18', "end": '1906-03-07', "qid": 'Q2426439'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Sarrien': {"start": '1906-03-14', "end": '1906-10-20', "qid": 'Q2685396'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Ferry_II': {"start": '1883-02-21', "end": '1885-03-30', "qid": 'Q3112182'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Méline': {"start": '1896-04-29', "end": '1898-06-28', "qid": 'Q2211955'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Léon_Bourgeois': {"start": '1895-11-01', "end": '1896-04-23', "qid": 'Q3112260'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Brisson_II': {"start": '1898-06-28', "end": '1898-10-26', "qid": 'Q3112113'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Casimir-Perier': {"start": '1893-12-03', "end": '1894-05-22', "qid": 'Q2657309'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Dupuy_I': {"start": '1893-04-04', "end": '1893-11-26', "qid": 'Q3111958'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Dupuy_II': {"start": '1894-05-30', "end": '1894-06-30', "qid": 'Q3111960'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Dupuy_III': {"start": '1894-07-02', "end": '1895-01-18', "qid": 'Q3111961'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Dupuy_V': {"start": '1899-02-18', "end": '1899-06-12', "qid": 'Q3111962'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Ribot_II': {"start": '1893-01-11', "end": '1893-03-31', "qid": 'Q3111855'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Briand_II': {"start": '1910-11-04', "end": '1911-02-27', "qid": 'Q3111889'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Doumergue_I': {"start": '1913-12-22', "end": '1914-06-02', "qid": 'Q3112055'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Combes': {"start": '1902-06-07', "end": '1905-01-18', "qid": 'Q1829373'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Caillaux': {"start": '1911-06-27', "end": '1912-01-14', "qid": 'Q2440172'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Monis': {"start": '1911-03-02', "end": '1911-06-23', "qid": 'Q2194496'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Poincaré_I': {"start": '1912-01-14', "end": '1913-01-21', "qid": 'Q3112407'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Dupuy_IV': {"start": '1898-11-01', "end": '1899-02-18', "qid": 'Q3111963'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Briand_III': {"start": '1913-01-21', "end": '1913-02-18', "qid": 'Q3111891'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Briand_IV': {"start": '1913-02-18', "end": '1913-03-22', "qid": 'Q3111893'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Viviani_I': {"start": '1914-06-13', "end": '1914-08-26', "qid": 'Q3112418'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Viviani_II': {"start": '1914-08-26', "end": '1915-10-28', "qid": 'Q1720449'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Barthou': {"start": '1913-03-22', "end": '1913-12-02', "qid": 'Q2431577'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Tardieu_III': {"start": '1932-02-20', "end": '1932-06-03', "qid": 'Q3111872'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Briand_XI': {"start": '1929-07-29', "end": '1929-10-22', "qid": 'Q3111887'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Poincaré_V': {"start": '1928-11-11', "end": '1929-07-26', "qid": 'Q3112413'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Tardieu_I': {"start": '1929-11-03', "end": '1930-02-17', "qid": 'Q3111874'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Laval_I': {"start": '1931-01-27', "end": '1931-06-13', "qid": 'Q3112376'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Laval_II': {"start": '1931-06-13', "end": '1932-01-12', "qid": 'Q3112379'},
    'https://fr.wikipedia.org/wiki/Gouvernement_François-Marsal': {"start": '1924-06-08', "end": '1924-06-10', "qid": 'Q2985797'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Ribot_IV': {"start": '1914-06-09', "end": '1914-06-12', "qid": 'Q3111859'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Steeg': {"start": '1930-12-13', "end": '1931-01-22', "qid": 'Q2842193'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Herriot_III': {"start": '1932-06-03', "end": '1932-12-14', "qid": 'Q3112687'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Laval_III': {"start": '1932-01-14', "end": '1932-02-06', "qid": 'Q3112382'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Chautemps_I': {"start": '1930-02-21', "end": '1930-02-25', "qid": 'Q3111941'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Chautemps_II': {"start": '1933-11-26', "end": '1934-01-27', "qid": 'Q3111946'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Daladier_I': {"start": '1933-01-30', "end": '1933-10-24', "qid": 'Q972341'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Daladier_II': {"start": '1934-01-30', "end": '1934-02-07', "qid": 'Q3112678'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Daladier_III': {"start": '1938-04-10', "end": '1939-05-11', "qid": 'Q3112680'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Herriot_II': {"start": '1926-07-19', "end": '1926-07-21', "qid": 'Q3112683'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Paul-Boncour': {"start": '1932-12-18', "end": '1933-01-28', "qid": 'Q2357748'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Poincaré_IV': {"start": '1926-07-23', "end": '1928-11-06', "qid": 'Q3112412'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Sarraut_I': {"start": '1933-10-26', "end": '1933-11-23', "qid": 'Q3111843'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Poincaré_III': {"start": '1924-03-29', "end": '1924-06-01', "qid": 'Q3112411'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Briand_VI': {"start": '1916-12-12', "end": '1917-03-20', "qid": 'Q3111896'},
    'https://fr.wikipedia.org/wiki/Gouvernement_de_la_Défense_nationale': {"start": '1870-09-04', "end": '1871-02-18', "qid": 'Q17358317'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Dufaure_I': {"start": '1871-02-19', "end": '1873-05-18', "qid": 'Q3112174'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Dufaure_II': {"start": '1873-05-18', "end": '1873-05-24', "qid": 'Q3112175'},
    'https://fr.wikipedia.org/wiki/Gouvernement_de_Broglie_I': {"start": '1873-05-25', "end": '1873-11-24', "qid": 'Q3111848'},
    'https://fr.wikipedia.org/wiki/Gouvernement_de_Broglie_II': {"start": '1873-11-26', "end": '1874-05-16', "qid": 'Q3111849'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Courtot_de_Cissey': {"start": '1874-05-22', "end": '1875-03-10', "qid": 'Q1860688'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Buffet': {"start": '1875-03-10', "end": '1876-02-23', "qid": 'Q2774993'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Dufaure_III': {"start": '1876-02-23', "end": '1876-03-09', "qid": 'Q3112177'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Dufaure_IV': {"start": '1876-03-09', "end": '1876-12-03', "qid": 'Q3112178'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Simon': {"start": '1876-12-12', "end": '1877-05-16', "qid": 'Q3112185'},
    'https://fr.wikipedia.org/wiki/Gouvernement_de_Broglie_III': {"start": '1877-05-17', "end": '1877-11-19', "qid": 'Q3111851'},
    'https://fr.wikipedia.org/wiki/Gouvernement_de_Rochebouët': {"start": '1877-11-23', "end": '1877-12-13', "qid": 'Q2212125'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Dufaure_V': {"start": '1877-12-13', "end": '1879-01-30', "qid": 'Q3112180'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Waddington': {"start": '1879-02-04', "end": '1879-12-21', "qid": 'Q2149902'},
    'https://fr.wikipedia.org/wiki/Gouvernement_de_Freycinet_I': {"start": '1879-12-28', "end": '1880-09-19', "qid": 'Q3111967'},
    'https://fr.wikipedia.org/wiki/Gouvernement_Ferry_I': {"start": '1880-09-23', "end": '1881-11-10', "qid": 'Q3112181'},
}

@dataclass
class CompositionRow:
    source_url: str
    page_title: str
    subsection: str | None
    table_index: int
    row_index: int
    position: str | None
    person_name: str | None
    person_wikipedia_url: str | None
    date_note: str | None
    parliamentary_group: str | None
    raw_text: str

@dataclass
class OutputRow:
    mandate__wikipedia_url: str
    mandate__name: str
    mandate__wikipedia_qid: str | None
    person_mandate__position: str | None
    person_mandate__group: str | None
    mandate__start_date: str | None
    mandate__end_date: str | None
    person_mandate__start_date: str | None
    person_mandate__end_date: str | None
    person__wikipedia_url: str | None
    person__wikidata_qid: str | None
    person__birth_date: str | None
    person__death_date: str | None
    person__last_name: str | None
    person__first_name: str | None

def normalize_space(text: str | None) -> str:
    if not text:
        return ""
    return WHITESPACE_RE.sub(" ", text.replace("\xa0", " ")).strip()

def wikipedia_title_from_url(url: str) -> str:
    parsed = urlparse(url)
    if "/wiki/" not in parsed.path:
        raise ValueError(f"Unsupported Wikipedia URL: {url}")
    slug = parsed.path.split("/wiki/", 1)[1]
    return unquote(slug).replace("_", " ")

def sleep_from_response(response: requests.Response | None, attempt: int) -> None:
    retry_after = None
    if response is not None:
        retry_after = response.headers.get("Retry-After")

    if retry_after:
        try:
            wait_s = float(retry_after)
        except ValueError:
            wait_s = min(60, 2 ** attempt)
    else:
        wait_s = min(60, 2 ** attempt)

    time.sleep(wait_s)

def mediawiki_get(
    session: requests.Session,
    params: dict,
    max_retries: int = 6,
    api_url: str = API_URL,
) -> dict:
    attempt = 0

    while True:
        response = session.get(
            api_url,
            params=params,
            headers=HEADERS,
            timeout=30,
        )

        if response.status_code == 429:
            attempt += 1
            if attempt > max_retries:
                response.raise_for_status()
            sleep_from_response(response, attempt)
            continue

        response.raise_for_status()
        data = response.json()

        error = data.get("error")
        if error and error.get("code") == "maxlag":
            attempt += 1
            if attempt > max_retries:
                raise RuntimeError(error)
            sleep_from_response(response, attempt)
            continue

        return data

def get_parse_payload(session: requests.Session, **params) -> dict:
    payload = mediawiki_get(
        session,
        {
            "action": "parse",
            "format": "json",
            "formatversion": "2",
            "maxlag": 5,
            **params,
        },
    )
    if "error" in payload:
        raise RuntimeError(payload["error"])
    return payload["parse"]

def find_composition_section_index(sections: list[dict]) -> str | None:
    for section in sections:
        label = normalize_space(section.get("line", "")).lower()
        if label in COMPOSITION_LABELS:
            return section.get("index")
    return None

def fetch_composition_html(session: requests.Session, title: str) -> str | None:
    parsed = get_parse_payload(session, page=title, prop="sections")
    section_index = find_composition_section_index(parsed.get("sections", []))
    if not section_index:
        return None
    section = get_parse_payload(session, page=title, prop="text", section=section_index)
    return section.get("text")

def extract_cell_text(cell) -> str:
    return normalize_space(cell.get_text("\n", strip=True))

def first_article_href(cell) -> str | None:
    for a in cell.find_all("a", href=True):
        href = a.get("href", "")
        if not href.startswith("/wiki/"):
            continue
        if href.startswith((
            "/wiki/Fichier:",
            "/wiki/File:",
            "/wiki/Cat%C3%A9gorie:",
            "/wiki/Category:",
            "/wiki/Aide:",
            "/wiki/Help:",
            "/wiki/Sp%C3%A9cial:",
            "/wiki/Special:",
            "/wiki/Discussion:",
        )):
            continue
        return BASE_WIKIPEDIA_URL + href
    return None

def clean_person_name(text: str | None) -> str | None:
    if not text:
        return None

    cleaned = normalize_space(text)
    cleaned = re.sub(r"\[\s*\d+\s*\]", "", cleaned)
    cleaned = re.sub(r"\bnote\s+\d+\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bnotes?\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+\]\s*$", "", cleaned)
    cleaned = re.sub(r"\s*\[\s*$", "", cleaned)
    cleaned = normalize_space(cleaned)
    return cleaned or None

def split_name_and_date(text: str) -> tuple[str | None, str | None]:
    cleaned = normalize_space(text)
    if not cleaned:
        return None, None

    match = re.search(r"\(\s*.*?\s*\)", cleaned, flags=re.IGNORECASE)
    if match:
        date_note = normalize_space(match.group(0).strip("()"))
        name = normalize_space(re.sub(r"\(\s*.*?\s*\)", "", cleaned, count=1, flags=re.IGNORECASE))
        return clean_person_name(name), date_note or None

    return clean_person_name(cleaned), None

def parse_french_date_to_iso(text: str | None) -> str | None:
    if not text:
        return None

    s = normalize_space(text.lower())
    s = s.replace("1er", "1")
    s = s.replace("’", "'")
    s = s.replace("'", " ")
    s = normalize_space(s)

    m = re.match(r"(\d{1,2})\s+([a-zéûôîàùç-]+)\s+(\d{4})", s)
    if not m:
        return None

    day, month_fr, year = m.groups()
    month = MONTHS_FR.get(month_fr)
    if not month:
        return None

    return f"{year}-{month}-{int(day):02d}"

def parse_date_note(date_note: str | None) -> tuple[str | None, str | None]:
    if not date_note:
        return None, None

    cleaned = normalize_space(date_note).replace("\n", " ").strip()

    m = re.search(r"^\s*du\s+(.+?)\s+au\s+(.+?)\s*$", cleaned, flags=re.IGNORECASE)
    if m:
        return parse_french_date_to_iso(m.group(1)), parse_french_date_to_iso(m.group(2))

    m = re.search(r"^\s*jusqu[’']?au\s+(.+?)\s*$", cleaned, flags=re.IGNORECASE)
    if m:
        return None, parse_french_date_to_iso(m.group(1))

    m = re.search(r"^\s*(à partir du|à compter du|depuis le)\s+(.+?)\s*$", cleaned, flags=re.IGNORECASE)
    if m:
        return parse_french_date_to_iso(m.group(2)), None

    return None, None

def table_to_rows(table, source_url: str, page_title: str, subsection: str | None, table_index: int) -> list[CompositionRow]:
    rows: list[CompositionRow] = []
    header_cells = [normalize_space(th.get_text(" ", strip=True)).lower() for th in table.find_all("th")]
    has_group_col = any("groupe" in h or "parti" in h for h in header_cells)
    last_position = None

    for row_index, tr in enumerate(table.find_all("tr"), start=1):
        cells = tr.find_all(["th", "td"], recursive=False)
        if not cells:
            continue

        visible_cells = []
        for c in cells:
            txt = extract_cell_text(c)
            if txt and "pas de photographie" not in txt.lower():
                visible_cells.append((c, txt))

        if not visible_cells:
            continue

        texts = [txt for _, txt in visible_cells]
        lowered = [t.lower() for t in texts]

        if any(t in {"fonction", "image", "nom", "groupe parlementaire", "parti politique"} for t in lowered):
            continue

        position = None
        person = None
        person_url = None
        date_note = None
        group = None

        if len(visible_cells) >= 3 and has_group_col:
            position = texts[0] or last_position
            person_cell, person_text = visible_cells[1]
            person, date_note = split_name_and_date(person_text)
            person_url = first_article_href(person_cell)
            group = texts[2] if len(texts) >= 3 else None

        elif len(visible_cells) == 2:
            if any(k in texts[0].lower() for k in ROLE_HINTS):
                position = texts[0]
                person_cell, person_text = visible_cells[1]
                person, date_note = split_name_and_date(person_text)
                person_url = first_article_href(person_cell)
            else:
                position = last_position
                person_cell, person_text = visible_cells[0]
                person, date_note = split_name_and_date(person_text)
                person_url = first_article_href(person_cell)
                group = texts[1]

        elif len(visible_cells) == 1:
            if any(k in texts[0].lower() for k in ROLE_HINTS):
                position = texts[0]
            else:
                position = last_position
                person_cell, person_text = visible_cells[0]
                person, date_note = split_name_and_date(person_text)
                person_url = first_article_href(person_cell)

        elif len(visible_cells) >= 4:
            position = texts[0] or last_position
            person_cell, person_text = visible_cells[1]
            person, date_note = split_name_and_date(person_text)
            person_url = first_article_href(person_cell)
            group = texts[-1]

        if position:
            last_position = position

        raw_text = " | ".join(texts)
        if position or person or group:
            rows.append(
                CompositionRow(
                    source_url=source_url,
                    page_title=page_title,
                    subsection=subsection,
                    table_index=table_index,
                    row_index=row_index,
                    position=position,
                    person_name=person,
                    person_wikipedia_url=person_url,
                    date_note=date_note,
                    parliamentary_group=group,
                    raw_text=raw_text,
                )
            )

    return rows

def parse_composition_html(html: str, source_url: str, page_title: str) -> list[CompositionRow]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[CompositionRow] = []
    subsection = None
    table_index = 0

    content_root = soup.select_one("div.mw-parser-output") or soup
    for element in content_root.children:
        name = getattr(element, "name", None)
        if name in {"h2", "h3", "h4"}:
            subsection = normalize_space(element.get_text(" ", strip=True)) or None
        elif name == "table":
            table_index += 1
            rows.extend(table_to_rows(element, source_url, page_title, subsection, table_index))

    return rows

def read_urls(args_urls: list[str], input_file: str | None) -> list[str]:
    urls = list(args_urls)
    if input_file:
        for line in Path(input_file).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    urls = [u for u in urls if u]
    if not urls:
        raise SystemExit("No URLs provided.")
    return urls

def split_french_person_name(full_name: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    if not full_name:
        return None, None

    tokens = normalize_space(full_name).split()

    if len(tokens) == 1:
        return tokens[0], None
    if len(tokens) == 2:
        return tokens[1], tokens[0]

    particles = {"de", "du", "des", "d'", "le", "la"}
    last_tokens = [tokens[-1]]
    i = len(tokens) - 2

    while i >= 0 and tokens[i].lower() in particles:
        last_tokens.insert(0, tokens[i])
        i -= 1

    first_tokens = tokens[: i + 1]
    if not first_tokens:
        return full_name, None

    return " ".join(last_tokens), " ".join(first_tokens)

def chunked(seq: list[str], size: int):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]

def wikipedia_urls_to_qids(
    session: requests.Session,
    wikipedia_urls: list[str],
    batch_size: int = 50,
) -> dict[str, str | None]:
    url_to_title: dict[str, str] = {}
    for url in wikipedia_urls:
        if not url:
            continue
        parsed = urlparse(url)
        if "/wiki/" not in parsed.path:
            continue
        slug = parsed.path.split("/wiki/", 1)[1]
        title = unquote(slug).replace("_", " ")
        url_to_title[url] = title

    title_to_qid: dict[str, str | None] = {title: None for title in url_to_title.values()}
    titles = list(title_to_qid.keys())

    for batch in chunked(titles, batch_size):
        data = mediawiki_get(
            session,
            {
                "action": "query",
                "format": "json",
                "formatversion": "2",
                "prop": "pageprops",
                "ppprop": "wikibase_item",
                "redirects": 1,
                "titles": "|".join(batch),
                "maxlag": 5,
            },
        )

        normalized_map = {
            item["to"]: item["from"]
            for item in data.get("query", {}).get("normalized", [])
            if item.get("to") and item.get("from")
        }
        redirect_map = {
            item["to"]: item["from"]
            for item in data.get("query", {}).get("redirects", [])
            if item.get("to") and item.get("from")
        }

        for page in data.get("query", {}).get("pages", []):
            resolved_title = page.get("title")
            qid = page.get("pageprops", {}).get("wikibase_item")

            if not resolved_title:
                continue

            candidates = {resolved_title}

            original_from_normalized = normalized_map.get(resolved_title)
            if original_from_normalized:
                candidates.add(original_from_normalized)

            original_from_redirect = redirect_map.get(resolved_title)
            if original_from_redirect:
                candidates.add(original_from_redirect)

            if original_from_redirect and original_from_redirect in normalized_map:
                candidates.add(normalized_map[original_from_redirect])

            for candidate in candidates:
                if candidate in title_to_qid:
                    title_to_qid[candidate] = qid

    return {url: title_to_qid.get(title) for url, title in url_to_title.items()}

def wikidata_qids_to_birth_death_dates(
    session: requests.Session,
    qids: list[str],
    batch_size: int = 50,
) -> dict[str, tuple[str | None, str | None]]:
    qid_map: dict[str, tuple[str | None, str | None]] = {qid: (None, None) for qid in qids if qid}
    unique_qids = list(qid_map.keys())

    def extract_date(entity: dict, prop_id: str) -> str | None:
        claims = entity.get("claims", {})
        if prop_id not in claims:
            return None
        try:
            date_val = claims[prop_id][0]["mainsnak"]["datavalue"]["value"]["time"]
            return date_val.lstrip("+").split("T", 1)[0]
        except (IndexError, KeyError, TypeError):
            return None

    for batch in chunked(unique_qids, batch_size):
        data = mediawiki_get(
            session,
            {
                "action": "wbgetentities",
                "format": "json",
                "ids": "|".join(batch),
                "props": "claims",
                "maxlag": 5,
            },
            api_url=WIKIDATA_API_URL,
        )

        entities = data.get("entities", {})
        for qid in batch:
            entity = entities.get(qid, {})
            qid_map[qid] = (extract_date(entity, "P569"), extract_date(entity, "P570"))

    return qid_map

def transform_rows(rows: Iterable[CompositionRow], session: requests.Session) -> list[OutputRow]:
    rows = list(rows)

    unique_urls = sorted({
        row.person_wikipedia_url
        for row in rows
        if row.person_wikipedia_url
    })
    qid_map = wikipedia_urls_to_qids(session, unique_urls)

    unique_qids = sorted({qid for qid in qid_map.values() if qid})
    birth_death_map = wikidata_qids_to_birth_death_dates(session, unique_qids)

    out: list[OutputRow] = []
    for row in rows:
        mandate_info = MANDATES.get(row.source_url, {})
        mandate_start = mandate_info.get("start")
        mandate_end = mandate_info.get("end")
        mandate_qid = mandate_info.get("qid")
        composition_start, composition_end = parse_date_note(row.date_note)
        last_name, first_name = split_french_person_name(row.person_name)
        qid = qid_map.get(row.person_wikipedia_url)
        birth_date, death_date = birth_death_map.get(qid, (None, None))

        out.append(
            OutputRow(
                mandate__wikipedia_url=row.source_url,
                mandate__name=row.page_title,
                mandate__wikipedia_qid=mandate_qid,
                person_mandate__position=row.position,
                person_mandate__group=row.parliamentary_group,
                mandate__start_date=mandate_start,
                mandate__end_date=mandate_end,
                person_mandate__start_date=composition_start,
                person_mandate__end_date=composition_end,
                person__wikipedia_url=row.person_wikipedia_url,
                person__wikidata_qid=qid,
                person__birth_date=birth_date,
                person__death_date=death_date,
                person__last_name=last_name,
                person__first_name=first_name,
            )
        )

    return out

def write_csv(rows: Iterable[OutputRow], output_path: str) -> None:
    fieldnames = [
        "mandate__name",
        "mandate__start_date",
        "mandate__end_date",
        "mandate__wikipedia_qid",
        "mandate__wikipedia_url",
        "person_mandate__position",
        "person_mandate__group",
        "person_mandate__start_date",
        "person_mandate__end_date",
        "person__last_name",
        "person__first_name",
        "person__birth_date",
        "person__death_date",
        "person__wikidata_qid",
        "person__wikipedia_url",
    ]

    with open(output_path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)

def main() -> None:
    parser = argparse.ArgumentParser(description="Extract composition rows from French Wikipedia government pages.")
    parser.add_argument("urls", nargs="*", help="Wikipedia page URLs")
    parser.add_argument("--input", help="Text file containing one Wikipedia URL per line")
    parser.add_argument("--output", default="ministers.csv", help="Output CSV path")
    args = parser.parse_args()

    urls = read_urls(args.urls, args.input)

    session = requests.Session()
    session.headers.update(HEADERS)

    rows: list[CompositionRow] = []
    for url in urls:
        title = wikipedia_title_from_url(url)
        html = fetch_composition_html(session, title)
        if not html:
            continue
        rows.extend(parse_composition_html(html, url, title))

    final_rows = transform_rows(rows, session)
    write_csv(final_rows, args.output)

if __name__ == "__main__":
    main()