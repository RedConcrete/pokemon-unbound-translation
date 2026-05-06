#!/usr/bin/env python3
"""
stats.py – Show translation progress for all languages at once.

Usage:
    python tools/stats.py
"""

import json
from pathlib import Path

TRANS_DIR = Path(__file__).parent.parent / "translations"

LANG_NAMES = {
    "de": "Deutsch 🇩🇪",
    "fr": "Français 🇫🇷",
    "es": "Español 🇪🇸",
    "it": "Italiano 🇮🇹",
    "pt": "Português 🇵🇹",
    "nl": "Nederlands 🇳🇱",
    "pl": "Polski 🇵🇱",
}


def bar(pct: int, width: int = 30) -> str:
    filled = int(width * pct / 100)
    return "█" * filled + "░" * (width - filled)


def main():
    print("\n── Pokémon Unbound Translation Progress ─────────────────────\n")
    found = False
    for lang_dir in sorted(TRANS_DIR.iterdir()):
        if not lang_dir.is_dir():
            continue
        json_files = list(lang_dir.glob("*.json"))
        if not json_files:
            continue
        found = True
        lang_code = lang_dir.name
        lang_name = LANG_NAMES.get(lang_code, lang_code.upper())
        data = json.loads(json_files[0].read_text(encoding="utf-8"))
        total = len(data)
        done = sum(1 for v in data.values() if v.get("done") and v.get("translation"))
        pct = round(done / total * 100) if total else 0
        print(f"  {lang_name:<20} {bar(pct)} {pct:3d}%  ({done:,}/{total:,})")

    if not found:
        print("  Keine Sprachdateien gefunden.")
        print("  Erstelle zuerst: python tools/create_language.py ...")
    print()


if __name__ == "__main__":
    main()
