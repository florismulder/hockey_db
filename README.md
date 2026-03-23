# Hockey DB — Tulp Hoofdklasse

Lokale database voor de **Tulp Hoofdklasse Heren** en **Livera Hoofdklasse Dames** seizoen 2025/26.

## Installatie

```bash
pip install -r requirements.txt
playwright install chromium
```

## Scripts

| Script | Beschrijving |
|---|---|
| `scripts/fetch_wikipedia.py` | Haalt standen en uitslagen op via de Nederlandse Wikipedia API |
| `scripts/fetch_hockey_nl_rss.py` | Haalt nieuws op via WordPress RSS feeds van hockey.nl |
| `scripts/scrape_tulp.py` | Scrapet het wedstrijdprogramma van tulphoofdklasse.com via Playwright |
| `scripts/update_db.py` | Orkestreert alle drie scripts met `--wiki`, `--rss` en `--tulp` opties |

## Gebruik

```bash
# Alles updaten
python scripts/update_db.py

# Individuele onderdelen
python scripts/update_db.py --wiki
python scripts/update_db.py --rss
python scripts/update_db.py --tulp

# Combinaties
python scripts/update_db.py --wiki --rss
```

---

## JSON Schema

### `competities/{heren|dames}/standen.json`

Gegenereerd door `fetch_wikipedia.py`.

```json
{
  "seizoen": "2025/26",
  "geslacht": "heren",
  "bron": "https://nl.wikipedia.org/wiki/Hoofdklasse_hockey_heren_2025/26",
  "bijgewerkt": "2025-10-01T12:00:00+00:00",
  "stand": [
    {
      "positie": 1,
      "club": "Amsterdam",
      "gespeeld": 10,
      "gewonnen": 8,
      "gelijk": 1,
      "verloren": 1,
      "doelpunten_voor": 30,
      "doelpunten_tegen": 10,
      "doelsaldo": 20,
      "punten": 25
    }
  ],
  "uitslagen": [
    {
      "datum": "01-09-2025",
      "thuis": "Amsterdam",
      "score_thuis": 3,
      "score_uit": 1,
      "uit": "Rotterdam"
    }
  ]
}
```

### `competities/{heren|dames}/programma.json`

Gegenereerd door `scrape_tulp.py`.

```json
{
  "seizoen": "2025/26",
  "geslacht": "heren",
  "bron": "https://tulphoofdklasse.com/en/matches-standings",
  "bijgewerkt": "2025-10-01T12:00:00+00:00",
  "wedstrijden": [
    {
      "datum": "15-10-2025",
      "tijd": "14:00",
      "thuis": "Amsterdam",
      "uit": "Rotterdam",
      "locatie": "Wagener Stadion",
      "gespeeld": false
    }
  ]
}
```

### `nieuws/{heren|dames}.json`

Gegenereerd door `fetch_hockey_nl_rss.py`.

```json
{
  "bron": "https://www.hockey.nl/competitie/hoofdklasse-heren/feed/",
  "bijgewerkt": "2025-10-01T12:00:00+00:00",
  "items": [
    {
      "guid": "https://www.hockey.nl/?p=12345",
      "titel": "Artikeltitel",
      "link": "https://www.hockey.nl/artikel/...",
      "datum": "2025-10-01T10:00:00+00:00",
      "samenvatting": "Korte beschrijving van het artikel...",
      "categorieen": ["Hoofdklasse", "Heren"],
      "afbeelding": "https://www.hockey.nl/wp-content/uploads/..."
    }
  ]
}
```

---

## Mappenstructuur

```
hockey_db/
├── competities/
│   ├── heren/
│   │   ├── standen.json       # Standen + uitslagen (Wikipedia)
│   │   ├── programma.json     # Komende wedstrijden (Tulp)
│   │   └── speelronden/       # Individuele speelronden (handmatig/toekomst)
│   └── dames/
│       ├── standen.json
│       ├── programma.json
│       └── speelronden/
├── clubs/                     # Clubprofielen
├── spelers/
│   ├── heren/
│   └── dames/
├── seizoenen/
│   └── 2025_2026/
├── scripts/
│   ├── __init__.py
│   ├── fetch_wikipedia.py
│   ├── fetch_hockey_nl_rss.py
│   ├── scrape_tulp.py
│   └── update_db.py
├── nieuws/
│   ├── heren.json
│   └── dames.json
└── output/
    ├── previews/
    ├── samenvattingen/
    └── analyses/
```
