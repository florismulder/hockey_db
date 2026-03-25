"""
Haalt nieuws op via hockey.nl feeds voor de Hoofdklasse en Oranje-teams.

Hoofdklasse feeds (gefilterd vanuit de algemene news_item feed op URL-pad):
    https://hockey.nl/?feed=rss2&post_type=news_item

Oranje- en jeugd-feeds (directe WordPress category feeds):
    https://www.hockey.nl/oranje/oranje-heren/feed/
    https://www.hockey.nl/oranje/oranje-dames/feed/
    https://www.hockey.nl/oranje/jong-oranje-heren/feed/
    https://www.hockey.nl/oranje/jong-oranje-dames/feed/
    https://www.hockey.nl/jeugd/jongens-o18/feed/
    https://www.hockey.nl/jeugd/meisjes-o18/feed/
    https://www.hockey.nl/jeugd/jongens-o16/feed/
    https://www.hockey.nl/jeugd/meisjes-o16/feed/

Output:
    nieuws/heren.json
    nieuws/dames.json
    nieuws/oranje-heren.json
    nieuws/oranje-dames.json
    nieuws/jong-oranje-heren.json
    nieuws/jong-oranje-dames.json
    nieuws/jongens-o18.json
    nieuws/meisjes-o18.json
    nieuws/jongens-o16.json
    nieuws/meisjes-o16.json
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import re

import feedparser
import requests
from bs4 import BeautifulSoup

# ── Configuratie ──────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent
NIEUWS_DIR = BASE_DIR / "nieuws"

# Algemene hockey.nl nieuws feed (custom post type)
HOOFDKLASSE_FEED_URL = "https://www.hockey.nl/?feed=rss2&post_type=news_item"

# URL-padfilters voor hoofdklasse categorisering
HEREN_PATH_FILTER = "/nieuws/tulp-hoofdklasse-heren/"
DAMES_PATH_FILTER = "/nieuws/tulp-hoofdklasse-dames/"

# Oranje & jeugd-nieuwspagina's (HTML-scraping, geen RSS beschikbaar)
ORANJE_FEEDS: dict[str, dict] = {
    "oranje-heren": {
        "url": "https://www.hockey.nl/oranje/oranje-heren/",
        "output": NIEUWS_DIR / "oranje-heren.json",
    },
    "oranje-dames": {
        "url": "https://www.hockey.nl/oranje/oranje-dames/",
        "output": NIEUWS_DIR / "oranje-dames.json",
    },
    "jong-oranje-heren": {
        "url": "https://www.hockey.nl/oranje/jong-oranje-heren",
        "output": NIEUWS_DIR / "jong-oranje-heren.json",
    },
    "jong-oranje-dames": {
        "url": "https://www.hockey.nl/oranje/jong-oranje-dames",
        "output": NIEUWS_DIR / "jong-oranje-dames.json",
    },
    "jongens-o18": {
        "url": "https://www.hockey.nl/jeugd/jongens-o18",
        "output": NIEUWS_DIR / "jongens-o18.json",
    },
    "meisjes-o18": {
        "url": "https://www.hockey.nl/jeugd/meisjes-o18",
        "output": NIEUWS_DIR / "meisjes-o18.json",
    },
    "jongens-o16": {
        "url": "https://www.hockey.nl/jeugd/jongens-o16",
        "output": NIEUWS_DIR / "jongens-o16.json",
    },
    "meisjes-o16": {
        "url": "https://www.hockey.nl/jeugd/meisjes-o16",
        "output": NIEUWS_DIR / "meisjes-o16.json",
    },
}

MAX_ITEMS = 50
SUMMARY_MAX_CHARS = 500
USER_AGENT = "HockeyDB/1.0 (github.com/hockey_db; data-only bot)"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ── RSS ophalen ───────────────────────────────────────────────────────────────

def fetch_feed(url: str) -> Optional[feedparser.FeedParserDict]:
    """Download en parseer een RSS-feed via requests + feedparser."""
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=20,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.error("Netwerkfout bij ophalen van '%s': %s", url, exc)
        return None

    # Sommige WordPress-feeds beginnen met newlines vóór de <?xml declaratie,
    # waardoor feedparser ze afwijst. Strip alles vóór de eerste XML/RSS tag.
    content = resp.content
    for marker in (b"<?xml", b"<rss", b"<feed"):
        idx = content.find(marker)
        if 0 < idx < 512:  # Alleen strippen bij een kleine offset (geen redirect-HTML)
            content = content[idx:]
            break

    feed = feedparser.parse(content)

    if feed.bozo and not feed.entries:
        log.error(
            "Feed '%s' kon niet worden geparseerd: %s",
            url,
            getattr(feed, "bozo_exception", "onbekende fout"),
        )
        return None

    if feed.bozo:
        log.warning(
            "Feed '%s' bevat ongeldige XML maar heeft %d entries; wordt toch verwerkt.",
            url,
            len(feed.entries),
        )

    return feed


# ── Entry parsing ─────────────────────────────────────────────────────────────

def _parse_date(entry: feedparser.FeedParserDict) -> str:
    """Converteer feedparser-datum naar ISO 8601 UTC-string."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
        except (TypeError, ValueError):
            pass
    return getattr(entry, "published", "")


def _strip_html(raw: str) -> str:
    """Verwijder HTML-tags en normaliseer witruimte."""
    text = BeautifulSoup(raw, "lxml").get_text(separator=" ", strip=True)
    if len(text) > SUMMARY_MAX_CHARS:
        text = text[: SUMMARY_MAX_CHARS - 3] + "..."
    return text


def _extract_image(entry: feedparser.FeedParserDict) -> str:
    """Probeer een thumbnail- of media-URL uit de entry te halen."""
    for attr in ("media_thumbnail", "media_content"):
        media = getattr(entry, attr, None)
        if media and isinstance(media, list) and media:
            url = media[0].get("url", "")
            if url:
                return url
    return ""


def parse_entries(
    feed: feedparser.FeedParserDict,
    path_filter: Optional[str] = None,
) -> list[dict]:
    """
    Zet RSS-entries om naar genormaliseerde nieuwsitems.

    Args:
        feed: Geparseerde feedparser feed.
        path_filter: Als opgegeven, alleen entries waarvan de link dit pad bevat.
    """
    items: list[dict] = []

    for entry in feed.entries:
        guid = getattr(entry, "id", getattr(entry, "link", ""))
        titel = getattr(entry, "title", "").strip()
        link = getattr(entry, "link", "")

        if not titel or not link:
            continue
        if path_filter and path_filter not in link:
            continue

        summary_raw = getattr(entry, "summary", "")
        item: dict = {
            "guid": guid,
            "titel": titel,
            "link": link,
            "datum": _parse_date(entry),
            "samenvatting": _strip_html(summary_raw) if summary_raw else "",
            "categorieen": [tag.term for tag in getattr(entry, "tags", [])],
        }

        image = _extract_image(entry)
        if image:
            item["afbeelding"] = image

        items.append(item)
        if len(items) >= MAX_ITEMS:
            break

    return items


# ── Samenvoegen & opslaan ─────────────────────────────────────────────────────

def load_existing(path: Path) -> list[dict]:
    """Laad bestaande items; retourneer lege lijst bij ontbrekend/corrupt bestand."""
    if not path.exists():
        return []
    try:
        with path.open(encoding="utf-8") as fh:
            return json.load(fh).get("items", [])
    except (json.JSONDecodeError, OSError, KeyError) as exc:
        log.warning("Kon bestaand bestand '%s' niet laden: %s", path, exc)
        return []


def merge_items(existing: list[dict], new_items: list[dict]) -> list[dict]:
    """Voeg nieuwe items samen, dedupliceer op GUID, sorteer op datum."""
    existing_guids = {item["guid"] for item in existing}
    fresh = [item for item in new_items if item["guid"] not in existing_guids]
    if fresh:
        log.info("%d nieuw(e) item(s) toegevoegd.", len(fresh))
    merged = fresh + existing
    merged.sort(key=lambda x: x.get("datum", ""), reverse=True)
    return merged[:MAX_ITEMS]


def save_news(items: list[dict], url: str, path: Path) -> None:
    """Sla nieuwsitems op als JSON-bestand."""
    path.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "bron": url,
        "bijgewerkt": datetime.now(timezone.utc).isoformat(),
        "items": items,
    }
    with path.open("w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=2)
    log.info("Opgeslagen: %s (%d items)", path, len(items))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _process_feed(
    label: str,
    url: str,
    output_path: Path,
    path_filter: Optional[str] = None,
) -> bool:
    """Haal één feed op, merge met bestaande data en sla op. Retourneert succes."""
    log.info("Ophalen feed '%s' ...", label)
    feed = fetch_feed(url)
    if feed is None:
        return False

    new_items = parse_entries(feed, path_filter=path_filter)
    log.info("  %d item(s) opgehaald%s.", len(new_items),
             f" (filter: {path_filter})" if path_filter else "")

    existing = load_existing(output_path)
    merged = merge_items(existing, new_items)

    try:
        save_news(merged, url, output_path)
        return True
    except OSError as exc:
        log.error("Fout bij opslaan van %s: %s", output_path, exc)
        return False


# ── HTML-scraping van nieuwspagina's (fallback voor Oranje/jeugd) ─────────────

def scrape_news_page(url: str) -> list[dict]:
    """
    Scrape nieuwsartikelen van een hockey.nl nieuwspagina.

    hockey.nl rendert nieuwsitems server-side als <li class="card card--news">.
    Elke kaart bevat een link, titel, datum en optioneel een afbeelding.
    """
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=20,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.error("Netwerkfout bij ophalen van '%s': %s", url, exc)
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    items: list[dict] = []

    # Zoek nieuwskaarten (.card--news of .card--a)
    cards = soup.select("li.card--news, li.card--a, article.card, .news-item")
    if not cards:
        # Fallback: zoek alle artikel-links in het hoofd-content-blok
        main = soup.find("main") or soup.find("div", class_=re.compile(r"content|main|wrapper"))
        if main:
            cards = main.find_all(["li", "article"], class_=re.compile(r"card|news|item"))

    log.debug("Nieuwskaarten gevonden op %s: %d", url, len(cards))

    for card in cards[:MAX_ITEMS]:
        # Link en titel
        a_tag = card.find("a", href=True)
        if not a_tag:
            continue
        link = a_tag.get("href", "")
        if not link.startswith("http"):
            link = f"https://www.hockey.nl{link}"

        # Titel: h2 of h3 in de kaart, of de link-tekst
        titel_el = card.find(["h2", "h3", "h4"]) or a_tag
        titel = titel_el.get_text(strip=True)
        if not titel or len(titel) < 3:
            continue

        # Datum: zoek een <time>-element of tekst met datumpatroon
        datum = ""
        time_el = card.find("time")
        if time_el:
            datum = time_el.get("datetime", time_el.get_text(strip=True))
        else:
            date_re = re.compile(r"\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}|\d{4}-\d{2}-\d{2}")
            for el in card.find_all(string=date_re):
                datum = el.strip()
                break

        # Afbeelding
        afbeelding = ""
        img = card.find("img")
        if img:
            afbeelding = img.get("src", img.get("data-src", ""))

        items.append({
            "guid": link,
            "titel": titel,
            "link": link,
            "datum": datum,
            "samenvatting": "",
            "categorieen": [],
            **({"afbeelding": afbeelding} if afbeelding else {}),
        })

    return items


def _process_news_page(label: str, url: str, output_path: Path) -> bool:
    """Scrape een nieuwspagina, merge met bestaande data en sla op."""
    log.info("Scraping nieuwspagina '%s' ...", label)
    new_items = scrape_news_page(url)
    log.info("  %d item(s) gevonden.", len(new_items))

    existing = load_existing(output_path)
    merged = merge_items(existing, new_items)

    try:
        save_news(merged, url, output_path)
        return True
    except OSError as exc:
        log.error("Fout bij opslaan van %s: %s", output_path, exc)
        return False


# ── Hoofdfunctie ──────────────────────────────────────────────────────────────

def main() -> dict[str, bool]:
    """
    Haal alle hockey.nl RSS feeds op en sla op.

    Returns:
        Dict met succes-status per feed-sleutel.
    """
    results: dict[str, bool] = {}

    # ── Hoofdklasse (gefilterd uit algemene feed) ──────────────────────────
    log.info("── Hoofdklasse nieuws ──")
    hoofdklasse_feed = fetch_feed(HOOFDKLASSE_FEED_URL)

    if hoofdklasse_feed is None:
        results["heren"] = False
        results["dames"] = False
    else:
        for geslacht, path_filter, out_path in [
            ("heren", HEREN_PATH_FILTER, NIEUWS_DIR / "heren.json"),
            ("dames", DAMES_PATH_FILTER, NIEUWS_DIR / "dames.json"),
        ]:
            new_items = parse_entries(hoofdklasse_feed, path_filter=path_filter)
            log.info("Hoofdklasse %s: %d item(s) (filter: %s)", geslacht, len(new_items), path_filter)
            existing = load_existing(out_path)
            merged = merge_items(existing, new_items)
            try:
                save_news(merged, HOOFDKLASSE_FEED_URL, out_path)
                results[geslacht] = True
            except OSError as exc:
                log.error("Fout bij opslaan van %s: %s", out_path, exc)
                results[geslacht] = False

    # ── Oranje en jeugd (HTML-scraping van nieuwspagina's) ────────────────
    # hockey.nl biedt geen bruikbare RSS per Oranje/jeugd-categorie;
    # de /feed/ URLs zijn comment-feeds. We scrapen de HTML-nieuwspagina's.
    log.info("── Oranje & jeugd nieuws ──")
    for key, config in ORANJE_FEEDS.items():
        results[key] = _process_news_page(key, config["url"], config["output"])

    return results


if __name__ == "__main__":
    success = main()
    sys.exit(0 if all(success.values()) else 1)
