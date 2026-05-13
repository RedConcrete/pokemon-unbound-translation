#!/usr/bin/env python3
"""
extract_text.py – Dumps all readable strings from a GBA Pokemon ROM.

Two-pass extraction:
  Pass 1 – Linear scan: walks every byte, applies byte-filter + quality check.
            Finds story text, NPC dialogs, item descriptions.
  Pass 2 – Pointer scan: finds all ROM-internal pointers (0x08xxxxxx),
            attempts to decode a string at the pointed-to offset.
            Finds menu strings, short UI labels, table-embedded text
            that the linear scan misses (wrong first-byte, short length).

Usage:
    python tools/extract_text.py <rom.gba> --output translations/en_source.json
    python tools/extract_text.py <rom.gba> --output translations/en_source.json --no-pointer-scan
"""

import re
import json
import struct
import argparse
from pathlib import Path

# ── FireRed / CFRU charset ─────────────────────────────────────────────────
FR_CHARSET = {
    0x00: " ",
    0x01: "À", 0x02: "Á", 0x03: "Â", 0x04: "Ç", 0x05: "È", 0x06: "É",
    0x07: "Ê", 0x08: "Ë", 0x09: "Ì", 0x0B: "Î", 0x0C: "Ï",
    0x0D: "Ò", 0x0E: "Ó", 0x0F: "Ô", 0x10: "Œ", 0x11: "Ù",
    0x12: "Ú", 0x13: "Û", 0x14: "Ñ", 0x15: "ß", 0x16: "à",
    0x17: "á", 0x19: "ç", 0x1A: "è", 0x1B: "é", 0x1C: "ê",
    0x1D: "ë", 0x1E: "ì", 0x20: "î", 0x21: "ï", 0x22: "ò",
    0x23: "ó", 0x24: "ô", 0x25: "œ", 0x26: "ù", 0x27: "ú",
    0x28: "û", 0x29: "ñ", 0x2A: "º", 0x2B: "ª", 0x2C: "·",
    0x2D: "&", 0x2E: "+",
    0x34: "[Lv]", 0x35: "=", 0x36: ";",
    0x51: "¿", 0x52: "¡",
    0x53: "[PK]", 0x54: "[MN]",
    0x55: "[PO]", 0x56: "[KE]",
    0x57: "[BL]", 0x58: "[OC]", 0x59: "[K]",
    0xA1: "0", 0xA2: "1", 0xA3: "2", 0xA4: "3", 0xA5: "4",
    0xA6: "5", 0xA7: "6", 0xA8: "7", 0xA9: "8", 0xAA: "9",
    0xAB: "!", 0xAC: "?", 0xAD: ".", 0xAE: "-",
    0xB0: "…", 0xB1: "\u201c", 0xB2: "\u201d", 0xB3: "\u2018", 0xB4: "\u2019",
    0xB5: "♂", 0xB6: "♀", 0xB7: "$", 0xB8: ",", 0xB9: "×",
    0xBA: "/", 0xBB: "A", 0xBC: "B", 0xBD: "C", 0xBE: "D",
    0xBF: "E", 0xC0: "F", 0xC1: "G", 0xC2: "H", 0xC3: "I",
    0xC4: "J", 0xC5: "K", 0xC6: "L", 0xC7: "M", 0xC8: "N",
    0xC9: "O", 0xCA: "P", 0xCB: "Q", 0xCC: "R", 0xCD: "S",
    0xCE: "T", 0xCF: "U", 0xD0: "V", 0xD1: "W", 0xD2: "X",
    0xD3: "Y", 0xD4: "Z", 0xD5: "a", 0xD6: "b", 0xD7: "c",
    0xD8: "d", 0xD9: "e", 0xDA: "f", 0xDB: "g", 0xDC: "h",
    0xDD: "i", 0xDE: "j", 0xDF: "k", 0xE0: "l", 0xE1: "m",
    0xE2: "n", 0xE3: "o", 0xE4: "p", 0xE5: "q", 0xE6: "r",
    0xE7: "s", 0xE8: "t", 0xE9: "u", 0xEA: "v", 0xEB: "w",
    0xEC: "x", 0xED: "y", 0xEE: "z",
    0xF9: "{COLOR}",     # 2-byte opcode: 0xF9 + 1 arg byte (color index)
    0xFA: "{HIGHLIGHT}", # 1-byte: scroll textbox up one line
    0xFB: "{SHADOW}",    # 1-byte: clear textbox entirely
    0xFC: "{DYNAMIC}",
    0xFF: "{END}",
}

# A-Z a-z bytes in FR charset
ASCII_LETTER_BYTES = set(range(0xBB, 0xEF))
# Accented letter bytes (é è à ê etc.) – 0x01–0x2F
ACCENTED_BYTES = set(range(0x01, 0x30))
ALL_LETTER_BYTES = ASCII_LETTER_BYTES | ACCENTED_BYTES

DIGIT_BYTES = set(range(0xA1, 0xAB))
PUNCT_BYTES = {
    0x00,  # space
    0xAB, 0xAC, 0xAD, 0xAE,        # ! ? . -
    0xB0, 0xB1, 0xB2, 0xB3, 0xB4,  # … " " ' '
    0xB5, 0xB6, 0xB7, 0xB8, 0xB9,  # ♂ ♀ $ , ×
    0xBA,                            # /
    0xFD, 0xFE,                      # \n \p (line breaks)
    0x2C, 0x2D, 0x2E,               # · & +
    0x34,                            # [Lv]
}

# ONLY 0xF9 (COLOR) takes an argument byte – 0xFA/0xFB are single-byte opcodes
ONE_ARG_CODES = {0xF9}

ALLOWED_BYTES = ALL_LETTER_BYTES | DIGIT_BYTES | PUNCT_BYTES | ONE_ARG_CODES | {0xFA, 0xFB}

# GBA ROM base address – all pointers stored as (0x08000000 + file_offset)
GBA_ROM_BASE = 0x08000000

# ── Inverse charset for re-encoding ───────────────────────────────────────
REVERSE_CHARSET: dict[str, int] = {}
for _byte, _char in FR_CHARSET.items():
    if _char not in REVERSE_CHARSET:
        REVERSE_CHARSET[_char] = _byte
REVERSE_CHARSET["\n"] = 0xFE
REVERSE_CHARSET["\\p"] = 0xFD


# ── Text quality filter ────────────────────────────────────────────────────
def _is_quality_text(text: str, min_ascii: int = 4, ratio: float = 0.50) -> bool:
    """
    Post-decode quality check. Returns True for strings that look like real game text.
    min_ascii / ratio are relaxed for pointer-scan candidates (short menu strings).
    """
    clean = re.sub(r'\{[^}]+\}', '', text)
    clean = clean.replace('\\p', '').replace('\\n', '')

    # Unknown opcode tokens → garbage (but allow {COLOR:XX} which preserves arg byte)
    _check_text = re.sub(r'\{COLOR:[0-9A-Fa-f]{2}\}', '', text)
    if re.search(r'\[\w{2,4}\]', _check_text):
        return False

    # 2+ consecutive accented chars at start → script opcodes, not text
    if re.search(r'^[\s]*[ÀÁÂÇÈÊËÌÎÏÒÓÔŒÙÚÛÑ]{2,}', text):
        return False

    # First real char must be ASCII-printable
    stripped = text.lstrip()
    if stripped and not stripped[0].isascii():
        return False

    ascii_letters = sum(1 for c in clean if c.isascii() and c.isalpha())
    if ascii_letters < min_ascii:
        return False

    non_space = len(clean.replace(' ', ''))
    if non_space > 0 and ascii_letters / non_space < ratio:
        return False

    # At least one word of 3+ chars must have a vowel
    words = re.findall(r'[A-Za-z]{3,}', clean)
    if words and not any(re.search(r'[aeiouAEIOU]', w) for w in words):
        return False

    # Reject repeating-pattern garbage (e.g. "AËBËCË", "N·G·N·G", "JgÔËPgÔË")
    # Check: if stripping non-ASCII leaves a pattern of length 1-3 repeated 4+ times
    non_ascii_stripped = re.sub(r'[^\x00-\x7F]', '', clean)
    if len(non_ascii_stripped) >= 6:
        # Check for simple character interleaving patterns
        for pat_len in (1, 2, 3):
            pat = non_ascii_stripped[:pat_len]
            if pat and all(
                non_ascii_stripped[i:i+pat_len] == pat
                for i in range(0, min(len(non_ascii_stripped), pat_len * 6), pat_len)
            ):
                return False

    # Reject if >40% of chars are non-ASCII accented (Ë Ô · etc.) — binary data
    total_chars = len(clean.replace(' ', ''))
    non_ascii_chars = sum(1 for c in clean if not c.isascii())
    if total_chars > 4 and non_ascii_chars / total_chars > 0.40:
        return False

    # Reject strings where COLOR tag appears but surrounding text is garbage
    # (binary data where 0xF9 happened to appear in the ROM)
    if re.search(r'\{COLOR:[0-9A-Fa-f]{2}\}', text):
        text_without_tags = re.sub(r'\{[^}]+\}', '', text).replace('\\p','').replace('\\n','')
        text_clean = text_without_tags.strip()
        real_letters = sum(1 for c in text_clean if c.isascii() and c.isalpha())
        real_words = re.findall(r'[A-Za-z]{3,}', text_clean)
        # Need at least one real word (3+ letters) with a vowel around the COLOR tag
        if not real_words or not any(re.search(r'[aeiouAEIOU]', w) for w in real_words):
            return False
        # Need at least 6 real ASCII letters (not just 'ie' + 'bc')
        if real_letters < 6:
            return False
        # Reject repeating ASCII patterns around the tag (e.g. RRRRURRR, hiizzz)
        ascii_only = re.sub(r'[^A-Za-z]', '', text_clean)
        if len(ascii_only) >= 4:
            for pat_len in (1, 2):
                pat = ascii_only[:pat_len]
                if pat and len(set(ascii_only[i:i+pat_len] for i in range(0, min(len(ascii_only), pat_len*5), pat_len))) <= 2:
                    return False
        # Reject if text around tag is >25% non-ASCII
        non_ascii_around = sum(1 for c in text_clean if not c.isascii())
        total_around = len(text_clean.replace(' ',''))
        if total_around > 3 and non_ascii_around / total_around > 0.25:
            return False

    return True


def _is_quality_text_strict(text: str) -> bool:
    """Standard quality check for linear scan (longer strings)."""
    return _is_quality_text(text, min_ascii=4, ratio=0.50)


def _is_quality_text_loose(text: str) -> bool:
    """Relaxed quality check for pointer-scan (short UI strings, names)."""
    # Extra guard: reject strings that start with lowercase (mid-sentence pointer)
    stripped = text.lstrip()
    if stripped and stripped[0].islower():
        return False
    # Reject strings starting with \p or \n (mid-string pointer)
    if text.startswith(('\\p', '\\n')):
        return False
    return _is_quality_text(text, min_ascii=2, ratio=0.40)


# ── GBA string decoder ─────────────────────────────────────────────────────
def decode_gba_string(data: bytes, offset: int, max_len: int = 512) -> tuple[str, int]:
    """Decode GBA string at offset. Returns (text, bytes_consumed)."""
    result = []
    i = offset
    while i < offset + max_len and i < len(data):
        b = data[i]
        if b == 0xFF:
            i += 1
            break
        elif b in ONE_ARG_CODES:
            # COLOR (0xF9): store arg byte in tag so encoder can restore it
            arg = data[i + 1] if i + 1 < len(data) else 0x00
            result.append(f"{{COLOR:{arg:02X}}}")
            i += 2
        elif b == 0xFA or b == 0xFB:
            result.append(FR_CHARSET.get(b, f"[{b:02X}]"))
            i += 1
        elif b == 0xFD:
            result.append("\\n")
            i += 1
        elif b == 0xFE:
            result.append("\\p")
            i += 1
        else:
            result.append(FR_CHARSET.get(b, f"[{b:02X}]"))
            i += 1
    return "".join(result), i - offset


# ── GBA string encoder ─────────────────────────────────────────────────────
def encode_gba_string(text: str) -> bytes:
    """Re-encode a Unicode string back to GBA bytes."""
    result = []
    i = 0
    while i < len(text):
        if text[i:i+2] == "\\n":
            result.append(0xFD)
            i += 2
        elif text[i:i+2] == "\\p":
            result.append(0xFE)
            i += 2
        elif text[i] == "{":
            end = text.find("}", i)
            token = text[i:end+1] if end != -1 else text[i:]
            # {COLOR:XX} – explicit arg byte from extraction
            if token.startswith("{COLOR:") and len(token) == 10:
                try:
                    arg = int(token[7:9], 16)
                except ValueError:
                    arg = 0x00
                result.append(0xF9)
                result.append(arg)
            else:
                byte = REVERSE_CHARSET.get(token)
                if byte is not None:
                    result.append(byte)
                    if byte == 0xF9:
                        result.append(0x00)  # fallback dummy arg for bare {COLOR}
            i = end + 1 if end != -1 else len(text)
        else:
            byte = REVERSE_CHARSET.get(text[i])
            result.append(byte if byte is not None else 0x00)
            i += 1
    result.append(0xFF)
    return bytes(result)


# ── Byte-level pre-filter (linear scan) ───────────────────────────────────
def _passes_byte_filter(data: bytes, offset: int, min_len: int) -> bool:
    """
    Fast byte-level check for the linear scan.
    First byte must be an ASCII letter or space. All bytes must be in ALLOWED set.
    """
    if offset >= len(data):
        return False
    first = data[offset]
    if first not in ASCII_LETTER_BYTES and first != 0x00:
        return False

    ascii_count = 0
    total = 0
    i = offset
    while i < len(data) and i < offset + 512:
        b = data[i]
        if b == 0xFF:
            if ascii_count < min_len:
                return False
            return total > 0 and (ascii_count / total) >= 0.45
        if b in ONE_ARG_CODES:
            i += 2
            total += 1
        elif b in (0xFA, 0xFB):
            i += 1
        elif b in ALLOWED_BYTES:
            if b in ASCII_LETTER_BYTES:
                ascii_count += 1
            if b not in (0xFD, 0xFE):
                total += 1
            i += 1
        else:
            return False
    return False


# ── Pointer scan helpers ───────────────────────────────────────────────────
def _passes_byte_filter_loose(data: bytes, offset: int) -> bool:
    """
    Relaxed byte filter for pointer-scan targets.
    Rules:
    - First byte must NOT be 0xFD (line-break \\n) or 0xFE (page-break \\p) — mid-string
    - First byte must NOT be a lowercase letter (0xD5-0xEE) — mid-sentence pointer
    - All bytes must be in ALLOWED set
    - Must terminate with 0xFF within 256 bytes
    - At least 3 ASCII letter bytes total
    """
    if offset >= len(data):
        return False

    first = data[offset]

    # Reject mid-string pointers: starts with \n, \p, {HIGHLIGHT}, {SHADOW}
    if first in (0xFD, 0xFE, 0xFA, 0xFB):
        return False

    # Reject mid-sentence pointers: starts with lowercase letter (0xD5=a … 0xEE=z)
    if 0xD5 <= first <= 0xEE:
        return False

    ascii_count = 0
    i = offset
    while i < len(data) and i < offset + 256:
        b = data[i]
        if b == 0xFF:
            return ascii_count >= 3
        if b in ONE_ARG_CODES:
            i += 2
        elif b in (0xFA, 0xFB):
            i += 1
        elif b in ALLOWED_BYTES:
            if b in ASCII_LETTER_BYTES:
                ascii_count += 1
            i += 1
        else:
            return False
    return False


def find_all_pointers(rom: bytes) -> set[int]:
    """
    Collect all unique file offsets that are pointed to by a valid GBA ROM pointer.
    A GBA ROM pointer is a little-endian uint32 in range [0x08000000, 0x08000000+romsize).
    We scan every 4-byte-aligned position.
    """
    rom_size = len(rom)
    targets: set[int] = set()
    # Only scan aligned positions for speed
    for i in range(0, rom_size - 4, 4):
        val = struct.unpack_from('<I', rom, i)[0]
        if GBA_ROM_BASE <= val < GBA_ROM_BASE + rom_size:
            file_offset = val - GBA_ROM_BASE
            targets.add(file_offset)
    return targets


# ── Pass 1: Linear scan ────────────────────────────────────────────────────
def extract_linear(rom: bytes, min_length: int) -> dict[str, dict]:
    """Standard linear scan – finds NPC dialogs, story text, item descriptions."""
    strings: dict[str, dict] = {}
    i = 0
    rom_len = len(rom)
    total = rom_len - 4
    last_pct = -1

    print("Pass 1 – Linear scan...")
    while i < total:
        pct = i * 100 // total
        if pct != last_pct:
            bar = "█" * (pct // 2) + "░" * (50 - pct // 2)
            print(f"\r  [{bar}] {pct:3d}%  {len(strings):,} strings", end="", flush=True)
            last_pct = pct

        if _passes_byte_filter(rom, i, min_length):
            text, consumed = decode_gba_string(rom, i)
            if _is_quality_text_strict(text):
                key = f"0x{i:07X}"
                strings[key] = {
                    "en": text,
                    "translation": "",
                    "comment": "",
                    "byte_offset": i,
                    "byte_length": consumed,
                }
                i += consumed
                continue
        i += 1

    print(f"\r  [{'█' * 50}] 100%  {len(strings):,} strings")
    return strings


# ── Pass 2: Pointer scan ───────────────────────────────────────────────────
def extract_pointer_scan(rom: bytes, already_found: set[int]) -> dict[str, dict]:
    """
    Follow every ROM-internal pointer and attempt to decode a string there.
    Catches menu labels, short UI strings, trainer class names that the
    linear scan misses due to wrong first-byte or short length.
    """
    print("Pass 2 – Collecting ROM pointers...", end=" ", flush=True)
    targets = find_all_pointers(rom)
    print(f"{len(targets):,} unique pointer targets found.")

    new_strings: dict[str, dict] = {}
    checked = 0
    found = 0

    print("Pass 2 – Decoding pointer targets...")
    targets_sorted = sorted(targets)
    total = len(targets_sorted)

    for idx, offset in enumerate(targets_sorted):
        if idx % 5000 == 0:
            pct = idx * 100 // total
            bar = "█" * (pct // 2) + "░" * (50 - pct // 2)
            print(f"\r  [{bar}] {pct:3d}%  {found:,} new strings", end="", flush=True)

        # Skip offsets already found by linear scan
        if offset in already_found:
            continue

        checked += 1

        if not _passes_byte_filter_loose(rom, offset):
            continue

        text, consumed = decode_gba_string(rom, offset, max_len=256)

        if not _is_quality_text_loose(text):
            continue

        key = f"0x{offset:07X}"
        new_strings[key] = {
            "en": text,
            "translation": "",
            "comment": "[pointer-scan]",
            "byte_offset": offset,
            "byte_length": consumed,
        }
        found += 1

    print(f"\r  [{'█' * 50}] 100%  {found:,} new strings ({checked:,} candidates checked)")
    return new_strings


# ── Main extraction ────────────────────────────────────────────────────────
def extract_all_strings(
    rom_path: str,
    min_length: int = 4,
    pointer_scan: bool = True,
) -> dict[str, dict]:

    rom = Path(rom_path).read_bytes()
    print(f"ROM size: {len(rom):,} bytes")

    # Pass 1 – linear
    strings = extract_linear(rom, min_length)
    print(f"Pass 1 done: {len(strings):,} strings\n")

    if pointer_scan:
        already_found = {v["byte_offset"] for v in strings.values()}
        new = extract_pointer_scan(rom, already_found)
        strings.update(new)
        print(f"Pass 2 done: +{len(new):,} new strings\n")

    # Sort by offset for clean JSON output
    sorted_strings = dict(
        sorted(strings.items(), key=lambda kv: kv[1]["byte_offset"])
    )
    print(f"Total: {len(sorted_strings):,} strings found.")
    return sorted_strings


def main():
    parser = argparse.ArgumentParser(
        description="Extract GBA Pokemon text to JSON (linear + pointer scan)"
    )
    parser.add_argument("rom", help="Path to .gba ROM file")
    parser.add_argument("--output", "-o", default="translations/en_source.json")
    parser.add_argument("--min-length", "-m", type=int, default=4,
                        help="Minimum ASCII letter count for linear scan (default: 4)")
    parser.add_argument("--no-pointer-scan", dest="pointer_scan",
                        action="store_false",
                        help="Skip pointer scan (faster, fewer results)")
    args = parser.parse_args()

    strings = extract_all_strings(
        args.rom,
        min_length=args.min_length,
        pointer_scan=args.pointer_scan,
    )

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(strings, f, ensure_ascii=False, indent=2)

    print(f"Saved: {out}")
    print(f"Next:  py tools/create_language.py {out} translations/de/de.json")


if __name__ == "__main__":
    main()