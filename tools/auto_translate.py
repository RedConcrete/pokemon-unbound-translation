#!/usr/bin/env python3
"""
auto_translate.py – Automatically translate strings using the Claude API.

Best suited for:
  - Pokémon names (don't translate, but can localize)
  - Attack/move names
  - Item names
  - Short UI strings

NOT suited for:
  - Long story dialogs (translate manually for quality)
  - Strings with many control codes

Usage:
    # Translate only specific offsets (e.g. a known range of Pokemon names)
    python tools/auto_translate.py translations/de/de.json --filter "Bulbasaur"

    # Translate all undone strings (careful – costs API tokens!)
    python tools/auto_translate.py translations/de/de.json --all

    # Translate only short strings (item/move names, max 30 chars)
    python tools/auto_translate.py translations/de/de.json --max-length 30

    # Dry run – show what would be translated without calling API
    python tools/auto_translate.py translations/de/de.json --max-length 30 --dry-run

Requirements:
    pip install anthropic
    Set ANTHROPIC_API_KEY environment variable:
      Windows: $env:ANTHROPIC_API_KEY = "sk-ant-..."
      Linux/Mac: export ANTHROPIC_API_KEY="sk-ant-..."
"""

import json
import os
import time
import argparse
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("ERROR: anthropic package not installed.")
    print("Run: pip install anthropic")
    exit(1)

TARGET_LANG = "Deutsch"
TARGET_CODE = "de"

SYSTEM_PROMPT = """Du bist ein Übersetzer für das Pokémon-Spiel "Pokémon Unbound" (GBA ROM-Hack).
Übersetze die gegebenen englischen Spieltexte ins Deutsche.

WICHTIGE REGELN:
- Behalte alle Control-Codes exakt bei: \\n \\p {PLAYER} {RIVAL} {SHADOW} {HIGHLIGHT} {COLOR} {DYNAMIC}
- Pokémon-Namen NICHT übersetzen (Pikachu bleibt Pikachu)
- Attacken-Namen können übersetzt werden wenn es eine offizielle deutsche Version gibt
- Verwende KEINE Umlaute (ä→ae, ö→oe, ü→ue, ß→ss) – der GBA-Zeichensatz unterstützt sie nicht
- Halte Zeilen kurz (max 34 Zeichen pro Zeile vor \\n oder \\p)
- Übersetze natürlich und flüssig, nicht wörtlich
- Antworte NUR mit dem übersetzten Text, ohne Erklärungen oder Anführungszeichen"""


def translate_batch(client: "anthropic.Anthropic", strings: list[dict]) -> list[str]:
    """
    Translate a batch of strings in one API call.
    strings: list of {"offset": ..., "en": ...}
    Returns: list of translated strings (same order)
    """
    # Build numbered list for the API
    numbered = "\n".join(f"{i+1}. {s['en']}" for i, s in enumerate(strings))

    prompt = f"""Übersetze diese {len(strings)} Spieltexte ins Deutsche.
Antworte mit einer nummerierten Liste im gleichen Format (1. Text, 2. Text, ...).
Behalte Zeilenumbrüche (\\n, \\p) und Control-Codes exakt bei.

{numbered}"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",  # Fast + cheap for batch translation
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    result_text = response.content[0].text.strip()

    # Parse numbered response
    translations = []
    lines = result_text.split("\n")
    current = []
    current_idx = 0

    for line in lines:
        import re
        m = re.match(r"^(\d+)\.\s*(.*)", line)
        if m:
            if current and current_idx > 0:
                translations.append("\n".join(current).strip())
            current = [m.group(2)]
            current_idx = int(m.group(1))
        elif current:
            current.append(line)

    if current:
        translations.append("\n".join(current).strip())

    # Pad if response was incomplete
    while len(translations) < len(strings):
        translations.append("")

    return translations[:len(strings)], response.usage


def auto_translate(lang_file: str, filter_text: str = None, max_length: int = None,
                   translate_all: bool = False, dry_run: bool = False,
                   batch_size: int = 20, delay: float = 0.5):

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY nicht gesetzt.")
        print("Windows: $env:ANTHROPIC_API_KEY = 'sk-ant-...'")
        print("Linux:   export ANTHROPIC_API_KEY='sk-ant-...'")
        exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    data = json.loads(Path(lang_file).read_text(encoding="utf-8"))

    # Select candidates
    candidates = []
    for offset, entry in data.items():
        if entry.get("done"):
            continue
        en = entry.get("en", "")

        if filter_text and filter_text.lower() not in en.lower():
            continue
        if max_length and len(en) > max_length:
            continue
        if not translate_all and not filter_text and not max_length:
            continue  # safety: don't translate everything without explicit flag

        candidates.append({"offset": offset, "en": en})

    if not candidates:
        print("Keine Kandidaten gefunden. Prüfe --filter / --max-length / --all")
        return

    print(f"Kandidaten zum Übersetzen: {len(candidates):,}")
    if dry_run:
        print("DRY RUN – kein API-Aufruf.")
        for c in candidates[:20]:
            print(f"  {c['offset']}: {c['en'][:70]}")
        if len(candidates) > 20:
            print(f"  … und {len(candidates)-20} weitere")
        return

    # Estimate cost (Haiku: ~$0.25/1M input tokens, ~$1.25/1M output tokens)
    avg_chars = sum(len(c['en']) for c in candidates) / len(candidates)
    est_tokens = len(candidates) * (avg_chars / 4 + 50)  # rough estimate
    est_cost = (est_tokens / 1_000_000) * 1.5
    print(f"Geschätzte Kosten: ~${est_cost:.3f} USD")
    confirm = input(f"Fortfahren? (j/n): ")
    if confirm.lower() not in ("j", "y", "ja", "yes"):
        print("Abgebrochen.")
        return

    # Translate in batches
    translated = 0
    failed = 0
    total_input_tokens = 0
    total_output_tokens = 0
    # Haiku pricing (per 1M tokens)
    PRICE_INPUT  = 0.80   # $0.80 per 1M input tokens
    PRICE_OUTPUT = 4.00   # $4.00 per 1M output tokens

    for batch_start in range(0, len(candidates), batch_size):
        batch = candidates[batch_start:batch_start + batch_size]
        batch_num = batch_start // batch_size + 1
        total_batches = (len(candidates) + batch_size - 1) // batch_size
        print(f"Batch {batch_num}/{total_batches} ({len(batch)} Strings)…", end=" ", flush=True)

        try:
            translations, usage = translate_batch(client, batch)
            total_input_tokens += usage.input_tokens
            total_output_tokens += usage.output_tokens
            for item, translation in zip(batch, translations):
                if translation.strip():
                    data[item["offset"]]["translation"] = translation.strip()
                    data[item["offset"]]["done"] = False  # Needs human review in editor
                    existing_comment = data[item["offset"]].get("comment", "")
                    if "[KI]" not in existing_comment:
                        data[item["offset"]]["comment"] = ("[KI] " + existing_comment).strip()
                    translated += 1
                else:
                    failed += 1
            ok = len([t for t in translations if t.strip()])
            cost_so_far = (total_input_tokens / 1e6 * PRICE_INPUT) + (total_output_tokens / 1e6 * PRICE_OUTPUT)
            print(f"✓ {ok} übersetzt  |  {usage.input_tokens}+{usage.output_tokens} Tokens  |  ~${cost_so_far:.4f} bisher")
        except Exception as e:
            print(f"✗ Fehler: {e}")
            failed += len(batch)

        # Save after each batch (don't lose progress)
        with open(lang_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        if batch_start + batch_size < len(candidates):
            time.sleep(delay)

    print()
    print(f"── Auto-Translate fertig ──────────────────────────")
    print(f"  Übersetzt : {translated:,}")
    print(f"  Fehler    : {failed:,}")
    total_cost = (total_input_tokens / 1e6 * PRICE_INPUT) + (total_output_tokens / 1e6 * PRICE_OUTPUT)
    print(f"  Gespeichert → {lang_file}")
    print()
    print(f"── Token-Verbrauch ────────────────────────────────")
    print(f"  Input-Tokens  : {total_input_tokens:,}")
    print(f"  Output-Tokens : {total_output_tokens:,}")
    print(f"  Gesamtkosten  : ~${total_cost:.4f} USD")
    print(f"  Modell        : claude-haiku-4-5 (günstigstes)")
    print("───────────────────────────────────────────────────")
    print()
    print("WICHTIG: Überprüfe die Übersetzungen im Editor!")
    print("KI-Übersetzungen sind ein Ausgangspunkt, kein Endprodukt.")


def main():
    parser = argparse.ArgumentParser(description="Auto-translate using Claude API")
    parser.add_argument("json", help="Sprachdatei (z.B. translations/de/de.json)")
    parser.add_argument("--filter", "-f", help="Nur Strings die diesen Text enthalten")
    parser.add_argument("--max-length", "-m", type=int, help="Nur Strings kürzer als X Zeichen")
    parser.add_argument("--all", action="store_true", help="Alle unübersetzten Strings (Vorsicht!)")
    parser.add_argument("--dry-run", action="store_true", help="Nur anzeigen, nicht übersetzen")
    parser.add_argument("--batch-size", type=int, default=20, help="Strings pro API-Aufruf (default: 20)")
    parser.add_argument("--delay", type=float, default=0.5, help="Sekunden zwischen Batches (default: 0.5)")
    args = parser.parse_args()

    auto_translate(
        args.json,
        filter_text=args.filter,
        max_length=args.max_length,
        translate_all=args.all,
        dry_run=args.dry_run,
        batch_size=args.batch_size,
        delay=args.delay,
    )


if __name__ == "__main__":
    main()
