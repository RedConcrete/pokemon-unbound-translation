#!/usr/bin/env python3
"""
stats.py – Show translation progress for all languages at once.

Usage:
    python tools/stats.py
"""

import json
import re
from pathlib import Path
from urllib.parse import quote

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


def compute_progress(lang_file: str) -> tuple[int, int, int]:
    data = json.loads(Path(lang_file).read_text(encoding="utf-8"))
    total = len(data)
    done = sum(1 for v in data.values() if v.get("done") and v.get("translation"))
    pct = round(done / total * 100) if total else 0
    return done, total, pct


def badge_color(pct: int) -> str:
    if pct < 30:
        return "red"
    if pct < 80:
        return "yellow"
    return "brightgreen"


def update_readme_progress(readme_path: Path, lang_file: str, lang_code: str = "de") -> bool:
    readme_path = Path(readme_path)
    if not readme_path.exists():
        return False

    done, total, pct = compute_progress(lang_file)
    if total == 0:
        return False

    lang_name = LANG_NAMES.get(lang_code, lang_code.upper())
    badge_name = {
        "de": "Deutsch",
        "fr": "Français",
        "es": "Español",
        "it": "Italiano",
        "pt": "Português",
        "nl": "Nederlands",
        "pl": "Polski",
    }.get(lang_code, lang_code.upper())
    badge_label = f"Fortschritt {lang_code.upper()}"
    badge_text = quote(badge_name)
    new_line = (
        f"![{badge_label}]"
        f"(https://img.shields.io/badge/{badge_text}-{pct}%25-{badge_color(pct)})"
    )

    pattern = (
        rf"!\[{re.escape(badge_label)}\]"
        rf"\(https://img\.shields\.io/badge/{re.escape(badge_name)}-[0-9]+%25-[^)]+\)"
    )

    content = readme_path.read_text(encoding="utf-8")
    new_content, count = re.subn(pattern, new_line, content)
    if count == 0:
        return False

    readme_path.write_text(new_content, encoding="utf-8")
    return True


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
