#!/usr/bin/env python3
"""
create_language.py – Fork the source JSON into a new language file.

Usage:
    python tools/create_language.py translations/en_source.json translations/de/de.json

This copies all English strings into a new file with empty "translation" fields.
Already-completed entries (non-empty "translation") are preserved on re-run.
"""

import json
import argparse
from pathlib import Path


LANGUAGE_NAMES = {
    "de": "Deutsch",
    "fr": "Français",
    "es": "Español",
    "it": "Italiano",
    "pt": "Português",
    "nl": "Nederlands",
    "pl": "Polski",
    "ru": "Русский",
    "ja": "日本語",
    "ko": "한국어",
    "zh": "中文",
}


def create_language(source_path: str, out_path: str):
    source = json.loads(Path(source_path).read_text(encoding="utf-8"))

    # Load existing target if it exists (preserve done work)
    existing: dict = {}
    target_file = Path(out_path)
    if target_file.exists():
        existing = json.loads(target_file.read_text(encoding="utf-8"))
        print(f"Merging with existing file: {out_path}")

    # Detect language code from filename
    lang_code = target_file.stem.split("_")[0]
    lang_name = LANGUAGE_NAMES.get(lang_code, lang_code.upper())

    output: dict = {}
    new_count = 0
    preserved_count = 0

    for offset, data in source.items():
        existing_entry = existing.get(offset, {})
        existing_translation = existing_entry.get("translation", "")

        output[offset] = {
            "en": data["en"],
            "translation": existing_translation,  # preserve if already done
            "comment": existing_entry.get("comment", data.get("comment", "")),
            "byte_offset": data["byte_offset"],
            "byte_length": data["byte_length"],
            "done": bool(existing_translation),
        }

        if existing_translation:
            preserved_count += 1
        else:
            new_count += 1

    # Stats
    total = len(output)
    done = preserved_count
    pct = (done / total * 100) if total else 0

    print(f"Language: {lang_name} ({lang_code})")
    print(f"Total strings : {total:,}")
    print(f"Already done  : {done:,} ({pct:.1f}%)")
    print(f"Still needed  : {new_count:,}")

    target_file.parent.mkdir(parents=True, exist_ok=True)
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Saved: {out_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Create or update a language translation file from the English source."
    )
    parser.add_argument("source", help="Path to en_source.json (from extract_text.py)")
    parser.add_argument("output", help="Output path, e.g. translations/de/de.json")
    args = parser.parse_args()

    create_language(args.source, args.output)


if __name__ == "__main__":
    main()
