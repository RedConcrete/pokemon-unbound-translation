#!/usr/bin/env python3
"""
extract_text.py – Dumps all readable strings from a GBA Pokemon ROM.

Usage:
    python tools/extract_text.py <rom.gba> --output translations/en_source.json
"""

import re
import json
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
    0xF9: "{COLOR}", 0xFA: "{HIGHLIGHT}",
    0xFB: "{SHADOW}", 0xFC: "{DYNAMIC}",
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
ONE_ARG_CODES = {0xF9, 0xFA, 0xFB}  # COLOR HIGHLIGHT SHADOW – next byte is arg
ALLOWED_BYTES = ALL_LETTER_BYTES | DIGIT_BYTES | PUNCT_BYTES | ONE_ARG_CODES

# ── Inverse charset for re-encoding ───────────────────────────────────────
REVERSE_CHARSET: dict[str, int] = {}
for _byte, _char in FR_CHARSET.items():
    if _char not in REVERSE_CHARSET:
        REVERSE_CHARSET[_char] = _byte
REVERSE_CHARSET["\n"] = 0xFE
REVERSE_CHARSET["\\p"] = 0xFD


# ── Text quality filter ────────────────────────────────────────────────────
def _is_quality_text(text: str) -> bool:
    """
    Post-decode quality check on the decoded Unicode string.
    Returns True only for strings that look like real game text.
    """
    # Strip control tokens for analysis
    clean = re.sub(r'\{[^}]+\}', '', text)
    clean = clean.replace('\\p', '').replace('\\n', '')

    # Reject: contains unknown opcode tokens like [0A] [1F] [2F]
    if re.search(r'\[\w{2,4}\]', text):
        return False

    # Reject: 2+ consecutive accented-as-garbage chars at start
    # (these appear as script opcodes, not real text)
    if re.search(r'^[\s]*[ÀÁÂÇÈÊËÌÎÏÒÓÔŒÙÚÛÑ]{2,}', text):
        return False

    # First non-space character must be ASCII-printable
    stripped = text.lstrip()
    if stripped and not stripped[0].isascii():
        return False

    # Count ASCII letters (A-Z a-z) – the reliable signal of real text
    ascii_letters = sum(1 for c in clean if c.isascii() and c.isalpha())

    # Need at least 4 real ASCII letters
    if ascii_letters < 4:
        return False

    # At least 50% of non-space chars must be ASCII letters
    non_space = len(clean.replace(' ', ''))
    if non_space > 0 and ascii_letters / non_space < 0.50:
        return False

    # Every word of 3+ chars must contain at least one vowel
    words = re.findall(r'[A-Za-z]{3,}', clean)
    if not words:
        return False
    if not any(re.search(r'[aeiouAEIOU]', w) for w in words):
        return False

    return True


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
            result.append(FR_CHARSET.get(b, f"[{b:02X}]"))
            i += 2
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
            byte = REVERSE_CHARSET.get(token)
            if byte is not None:
                result.append(byte)
            i = end + 1 if end != -1 else len(text)
        else:
            byte = REVERSE_CHARSET.get(text[i])
            result.append(byte if byte is not None else 0x00)
            i += 1
    result.append(0xFF)
    return bytes(result)


# ── Byte-level pre-filter ──────────────────────────────────────────────────
def _passes_byte_filter(data: bytes, offset: int, min_len: int) -> bool:
    """
    Fast byte-level check before decoding.
    - First byte must be ASCII letter or space (0xBB–0xEE or 0x00)
    - Must terminate with 0xFF within 512 bytes
    - Must have enough ASCII letter bytes
    - All bytes must be in ALLOWED set
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
        elif b in ALLOWED_BYTES:
            if b in ASCII_LETTER_BYTES:
                ascii_count += 1
            if b not in (0xFD, 0xFE):
                total += 1
            i += 1
        else:
            return False
    return False


# ── Main extraction ────────────────────────────────────────────────────────
def extract_all_strings(rom_path: str, min_length: int = 4) -> dict[str, dict]:
    rom = Path(rom_path).read_bytes()
    strings: dict[str, dict] = {}
    i = 0
    rom_len = len(rom)
    total = rom_len - 4
    last_pct = -1

    print(f"ROM size: {rom_len:,} bytes")
    print("Scanning for strings...")

    while i < total:
        pct = i * 100 // total
        if pct != last_pct:
            bar = "█" * (pct // 2) + "░" * (50 - pct // 2)
            print(f"\r  [{bar}] {pct:3d}%  {len(strings):,} strings", end="", flush=True)
            last_pct = pct

        if _passes_byte_filter(rom, i, min_length):
            text, consumed = decode_gba_string(rom, i)
            if _is_quality_text(text):
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
    print(f"Done. Found {len(strings):,} strings.")
    return strings


def main():
    parser = argparse.ArgumentParser(description="Extract GBA Pokemon text to JSON")
    parser.add_argument("rom", help="Path to .gba ROM file")
    parser.add_argument("--output", "-o", default="translations/en_source.json")
    parser.add_argument("--min-length", "-m", type=int, default=4)
    args = parser.parse_args()

    strings = extract_all_strings(args.rom, args.min_length)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(strings, f, ensure_ascii=False, indent=2)

    print(f"Saved: {out}")
    print(f"Next:  py tools/create_language.py {out} translations/de/de.json")


if __name__ == "__main__":
    main()