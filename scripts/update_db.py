"""
Orkestreert alle data-ophaalscripts voor de Hockey DB.

Gebruik:
    python scripts/update_db.py              # voer alles uit
    python scripts/update_db.py --wiki       # alleen Wikipedia standen
    python scripts/update_db.py --rss        # alleen hockey.nl nieuws
    python scripts/update_db.py --tulp       # alleen Tulp scraper
    python scripts/update_db.py --oranje     # alleen Oranje selecties
    python scripts/update_db.py --wiki --rss # combineer naar keuze
"""

import argparse
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Voeg de scripts-map toe aan sys.path zodat imports werken
# ongeacht vanuit welke werkdirectory het script wordt aangeroepen.
sys.path.insert(0, str(Path(__file__).parent))

import fetch_wikipedia
import fetch_hockey_nl_rss
import scrape_tulp
import fetch_oranje_selecties

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ── Rapportage ────────────────────────────────────────────────────────────────

def _icon(ok: bool) -> str:
    return "✓" if ok else "✗"


def print_report(
    results: dict[str, dict[str, bool]],
    durations: dict[str, float],
) -> None:
    """Druk een overzichtelijk eindrapport af op stdout."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    width = 60

    print()
    print("=" * width)
    print(f"  Hockey DB — Update rapport  ({timestamp})")
    print("=" * width)

    all_ok = True
    for script_name, script_results in results.items():
        duration = durations.get(script_name, 0.0)
        overall = all(script_results.values()) if script_results else False
        all_ok = all_ok and overall

        print(f"\n  {_icon(overall)}  {script_name}  ({duration:.1f}s)")
        for key, ok in script_results.items():
            print(f"       {_icon(ok)}  {key}")

    print()
    print("─" * width)
    if all_ok:
        print("  Alle taken succesvol afgerond.")
    else:
        n_failed = sum(1 for sr in results.values() for ok in sr.values() if not ok)
        print(f"  {n_failed} taak/taken mislukt — zie de logs hierboven.")
    print("=" * width)
    print()


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update de Hockey DB door externe databronnen op te halen.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Voorbeelden:\n"
            "  python scripts/update_db.py              # alles updaten\n"
            "  python scripts/update_db.py --wiki       # alleen Wikipedia\n"
            "  python scripts/update_db.py --rss        # alleen nieuws\n"
            "  python scripts/update_db.py --tulp       # alleen programma\n"
            "  python scripts/update_db.py --oranje     # alleen selecties\n"
            "  python scripts/update_db.py --wiki --rss # twee bronnen\n"
        ),
    )
    parser.add_argument(
        "--wiki",
        action="store_true",
        help="Haal standen en uitslagen op via Nederlandse Wikipedia",
    )
    parser.add_argument(
        "--rss",
        action="store_true",
        help="Haal nieuws op via hockey.nl RSS feeds (Hoofdklasse + Oranje)",
    )
    parser.add_argument(
        "--tulp",
        action="store_true",
        help="Scrape wedstrijdresultaten en programma van tulphoofdklasse.com",
    )
    parser.add_argument(
        "--oranje",
        action="store_true",
        help="Haal Oranje-selecties op en detecteer wijzigingen",
    )
    return parser.parse_args()


# ── Taakuitvoering ────────────────────────────────────────────────────────────

def _run(label: str, func) -> tuple[dict[str, bool], float]:
    """
    Voer een script-main()-functie uit, meet de duur en vang onverwachte fouten op.

    Returns:
        Tuple (resultaten_dict, duur_in_seconden).
    """
    log.info("━━ %s ━━", label)
    t0 = time.monotonic()
    try:
        result = func()
    except Exception as exc:
        log.error("Onverwachte fout in %s: %s", label, exc, exc_info=True)
        result = {}
    return result, time.monotonic() - t0


# ── Hoofdfunctie ──────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()

    # Geen vlaggen opgegeven → alles uitvoeren
    run_all = not any([args.wiki, args.rss, args.tulp, args.oranje])

    report: dict[str, dict[str, bool]] = {}
    durations: dict[str, float] = {}

    if run_all or args.wiki:
        res, dur = _run("Wikipedia standen ophalen", fetch_wikipedia.main)
        report["fetch_wikipedia"] = res
        durations["fetch_wikipedia"] = dur

    if run_all or args.rss:
        res, dur = _run("hockey.nl RSS-nieuws ophalen", fetch_hockey_nl_rss.main)
        report["fetch_hockey_nl_rss"] = res
        durations["fetch_hockey_nl_rss"] = dur

    if run_all or args.tulp:
        res, dur = _run("Tulp wedstrijdresultaten scrapen", scrape_tulp.main)
        report["scrape_tulp"] = res
        durations["scrape_tulp"] = dur

    if run_all or args.oranje:
        res, dur = _run("Oranje selecties ophalen", fetch_oranje_selecties.main)
        report["fetch_oranje_selecties"] = res
        durations["fetch_oranje_selecties"] = dur

    print_report(report, durations)

    all_ok = all(ok for sr in report.values() for ok in sr.values())
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
