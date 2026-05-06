#!/usr/bin/env python3
"""
update_translation.py – Merge a new Unbound version's strings into existing translations.

When Unbound v2.x releases, run this to:
  1. See what's NEW  (strings not in old version)
  2. See what CHANGED (same offset, different English text)
  3. See what REMOVED (offset no longer exists)

Usage:
    python tools/update_translation.py \\
        translations/en_source.json \\       ← old extraction
        translations/en_source_v2.json \\    ← new extraction (run extract_text.py on new ROM)
        translations/de/de.json             ← your existing translation (UPDATED IN PLACE)

Output:
    translations/de/de.json  – updated (new entries added as empty, changed entries flagged)
    translations/de/update_report_<date>.txt
"""

import json
import argparse
from datetime import datetime
from pathlib import Path


def update(old_source: str, new_source: str, lang_file: str):
    old = json.loads(Path(old_source).read_text(encoding="utf-8"))
    new = json.loads(Path(new_source).read_text(encoding="utf-8"))
    lang = json.loads(Path(lang_file).read_text(encoding="utf-8"))

    new_entries = []
    changed_entries = []
    removed_offsets = []

    updated_lang: dict = {}

    # Process all offsets in new source
    for offset, new_data in new.items():
        old_data = old.get(offset)
        existing_trans = lang.get(offset, {})

        if old_data is None:
            # Brand new string
            updated_lang[offset] = {
                "en": new_data["en"],
                "translation": "",
                "comment": "⚡ NEU in dieser Version",
                "byte_offset": new_data["byte_offset"],
                "byte_length": new_data["byte_length"],
                "done": False,
            }
            new_entries.append(offset)
        elif old_data["en"] != new_data["en"]:
            # String changed
            old_trans = existing_trans.get("translation", "")
            updated_lang[offset] = {
                "en": new_data["en"],
                "translation": "",  # reset – needs re-translation
                "comment": f"⚠ GEÄNDERT. Alt-EN: {old_data['en'][:80]} | Alt-DE: {old_trans[:60]}",
                "byte_offset": new_data["byte_offset"],
                "byte_length": new_data["byte_length"],
                "done": False,
            }
            changed_entries.append(offset)
        else:
            # Unchanged – carry over existing translation
            updated_lang[offset] = {
                "en": new_data["en"],
                "translation": existing_trans.get("translation", ""),
                "comment": existing_trans.get("comment", ""),
                "byte_offset": new_data["byte_offset"],
                "byte_length": new_data["byte_length"],
                "done": existing_trans.get("done", False),
            }

    # Find removed offsets
    for offset in old:
        if offset not in new:
            removed_offsets.append(offset)

    # Save updated lang file
    lang_path = Path(lang_file)
    with open(lang_path, "w", encoding="utf-8") as f:
        json.dump(updated_lang, f, ensure_ascii=False, indent=2)

    # Write report
    date_str = datetime.now().strftime("%Y-%m-%d_%H%M")
    report_path = lang_path.parent / f"update_report_{date_str}.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"Update Report – {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Neue Einträge   : {len(new_entries)}\n")
        f.write(f"Geänderte EN    : {len(changed_entries)}\n")
        f.write(f"Entfernte Offsets: {len(removed_offsets)}\n\n")

        if new_entries:
            f.write("── NEUE STRINGS ─────────────────────────────────────\n")
            for o in new_entries:
                f.write(f"  {o}: {new[o]['en'][:80]}\n")
            f.write("\n")

        if changed_entries:
            f.write("── GEÄNDERTE STRINGS (müssen neu übersetzt werden) ─\n")
            for o in changed_entries:
                f.write(f"  {o}:\n")
                f.write(f"    ALT: {old[o]['en'][:80]}\n")
                f.write(f"    NEU: {new[o]['en'][:80]}\n")
            f.write("\n")

        if removed_offsets:
            f.write("── ENTFERNTE OFFSETS ────────────────────────────────\n")
            for o in removed_offsets:
                f.write(f"  {o}: {old[o]['en'][:80]}\n")

    total = len(updated_lang)
    done = sum(1 for v in updated_lang.values() if v.get("done"))
    pct = round(done / total * 100) if total else 0

    print(f"Neue Einträge     : {len(new_entries)}")
    print(f"Geänderte Strings : {len(changed_entries)}")
    print(f"Entfernte Offsets : {len(removed_offsets)}")
    print(f"Fortschritt       : {done}/{total} ({pct}%)")
    print(f"Sprachdatei   → {lang_file}")
    print(f"Report        → {report_path}")


def main():
    parser = argparse.ArgumentParser(description="Update translation file for new Unbound version")
    parser.add_argument("old_source", help="Old en_source.json")
    parser.add_argument("new_source", help="New en_source.json (extracted from updated ROM)")
    parser.add_argument("lang_file",  help="Your translation file to update (e.g. translations/de/de.json)")
    args = parser.parse_args()
    update(args.old_source, args.new_source, args.lang_file)


if __name__ == "__main__":
    main()
