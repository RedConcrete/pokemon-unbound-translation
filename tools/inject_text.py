#!/usr/bin/env python3
"""
inject_text.py – Inject translated strings back into the GBA ROM.

Usage:
    python tools/inject_text.py <source.gba> translations/de/de.json --output output/unbound_de.gba

IMPORTANT:
  - Only injects strings where "done": true AND "translation" is non-empty.
  - Strings can NOT be longer (in bytes) than the original. If they are,
    the script warns and skips that entry.
  - Always work on a COPY of the ROM – never overwrite the original!

String length budget trick:
  German text tends to be longer than English. Use abbreviations where needed:
    Pokémon  → Pokémon (same)
    Mission  → Mission (same)
    Trainer  → Trainer (same)
  Keep \\n and \\p line breaks; they don't count as translated characters.
"""

import json
import shutil
import argparse
from pathlib import Path

# Re-use encoder from extract_text
import sys
sys.path.insert(0, str(Path(__file__).parent))
from extract_text import encode_gba_string


def inject(source_rom: str, lang_json: str, output_rom: str, dry_run: bool = False):
    # Load ROM
    rom_data = bytearray(Path(source_rom).read_bytes())
    translations = json.loads(Path(lang_json).read_text(encoding="utf-8"))

    injected = 0
    skipped_not_done = 0
    skipped_too_long = 0
    errors = 0
    too_long_list = []

    for offset_str, entry in translations.items():
        if not entry.get("done"):
            skipped_not_done += 1
            continue
        translation = entry.get("translation", "").strip()
        if not translation:
            skipped_not_done += 1
            continue

        offset = entry["byte_offset"]
        original_len = entry["byte_length"]

        try:
            encoded = encode_gba_string(translation)
        except Exception as e:
            print(f"⚠ Encode error at {offset_str}: {e}")
            errors += 1
            continue

        # Length check: encoded must fit in original space
        if len(encoded) > original_len:
            over = len(encoded) - original_len
            print(
                f"⚠ SKIP {offset_str}: translation too long "
                f"(+{over} bytes). Original: {original_len}b, "
                f"Translated: {len(encoded)}b"
            )
            print(f"   EN : {entry['en'][:60]}")
            print(f"   DE : {translation[:60]}")
            too_long_list.append({
                'offset': offset_str,
                'over': over,
                'used': len(encoded),
                'max': original_len,
                'en': entry['en'],
                'de': translation,
            })
            skipped_too_long += 1
            continue

        if not dry_run:
            # Pad with 0xFF (END) to fill original space
            padded = encoded + bytes([0xFF] * (original_len - len(encoded)))
            rom_data[offset : offset + original_len] = padded

        injected += 1

    print()
    print("── Injection Summary ──────────────────────────────")
    print(f"  Injected   : {injected:,}")
    print(f"  Not done   : {skipped_not_done:,}")
    print(f"  Too long   : {skipped_too_long:,}  ← shorten these!")
    print(f"  Errors     : {errors:,}")
    print("───────────────────────────────────────────────────")
    if too_long_list:
        print()
        print("── Zu lange Strings ───────────────────────────────")
        for item in too_long_list:
            print(f"  {item['offset']}  +{item['over']}b  ({item['used']}b / {item['max']}b)")
            print(f"    EN : {item['en'][:70]}")
            print(f"    DE : {item['de'][:70]}")
        print("───────────────────────────────────────────────────")

    if dry_run:
        print("DRY RUN – no file written.")
        return

    out = Path(output_rom)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(rom_data)
    print(f"ROM written: {out}")


def main():
    parser = argparse.ArgumentParser(description="Inject translated strings into GBA ROM")
    parser.add_argument("rom",     help="Source .gba file (Pokémon Unbound patched)")
    parser.add_argument("json",    help="Translation JSON (e.g. translations/de/de.json)")
    parser.add_argument("--output", "-o", default="output/unbound_translated.gba")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simulate injection without writing (shows length errors)")
    args = parser.parse_args()

    inject(args.rom, args.json, args.output, dry_run=args.dry_run)


if __name__ == "__main__":
    main()