# Pokémon Unbound – Translation Toolkit

Multi-language translation pipeline für Pokémon Unbound (GBA ROM-Hack).

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Fortschritt DE](https://img.shields.io/badge/Deutsch-0%25-red)
![Lizenz](https://img.shields.io/badge/Lizenz-MIT-green)

## Quick Start

### 1. Text extrahieren
```powershell
py tools/extract_text.py "Pokemon Unbound (v2.1.1.1).gba" --output translations/en_source.json
```
Erzeugt `en_source.json` mit allen Strings aus der ROM.

### 2. Sprachdatei erstellen
```powershell
py tools/create_language.py translations/en_source.json translations/de/de.json
```

### 3. Im Browser übersetzen
- `tools/editor.html` öffnen
- Datei laden: `translations/de/de.json`
- Englisch links lesen → Deutsch rechts eingeben
- Speichern → zurück nach `translations/de/de.json` kopieren

### 4. ROM bauen
```powershell
py tools/inject_text.py "Pokemon Unbound (v2.1.1.1).gba" translations/de/de.json --output output/unbound_de.gba
```
Der Progress-Badge wird automatisch aktualisiert!

### 5. Dry-Run (optional)
```powershell
py tools/inject_text.py "Pokemon Unbound (v2.1.1.1).gba" translations/de/de.json --dry-run
```
Zeigt zu lange Strings an, verändert die ROM nicht.

---

## Alle Tools

| Befehl | Zweck |
|--------|-------|
| `extract_text.py` | Text aus ROM extrahieren |
| `create_language.py` | Neue Sprachdatei erstellen |
| `editor.html` | Browser-Editor zum Übersetzen |
| `inject_text.py` | Übersetzung in ROM schreiben (+ auto README-Update) |
| `auto_translate.py` | KI-Vorabübersetzung via Claude API |
| `update_translation.py` | Neue Unbound-Version mergen |
| `stats.py` | Fortschritt aller Sprachen anzeigen |

---

## KI-Vorabübersetzung (optional)

```powershell
pip install anthropic

# API Key setzen (Windows PowerShell)
$env:ANTHROPIC_API_KEY = "sk-ant-..."

# Kurze Strings übersetzen (empfohlen)
py tools/auto_translate.py translations/de/de.json --max-length 30

# Oder spezifischen Text filtern
py tools/auto_translate.py translations/de/de.json --filter "Item"

# Dry-run (keine API-Kosten)
py tools/auto_translate.py translations/de/de.json --max-length 30 --dry-run
```

KI-Strings werden mit `[KI]` markiert und müssen manuell im Editor geprüft werden.

---

## Bekannte Einschränkungen

**Stringlänge:** Deutsche Texte sind oft 20–30% länger. Mit `--dry-run` prüfen, welche zu lang sind.

**Sonderzeichen:** Bei Anzeigefehlern mit ä/ö/ü folgende Fallbacks nutzen:
- `ä` → `ae`, `ö` → `oe`, `ü` → `ue`, `ß` → `ss`

**Control-Codes bewahren:**
- `\n` = Zeilenumbruch
- `\p` = Seitenumbruch
- `{PLAYER}`, `{RIVAL}`, `{COLOR}`, etc.

---

## Workflow für neue Unbound-Version

```powershell
# 1. Neue ROM extrahieren
py tools/extract_text.py "Pokemon Unbound (v2.2).gba" --output translations/en_source_new.json

# 2. Merge → behält fertige Übersetzungen
py tools/update_translation.py translations/en_source.json translations/en_source_new.json translations/de/de.json

# 3. Alte Source ersetzen
copy translations\en_source_new.json translations\en_source.json

# 4. Im Editor neue Strings übersetzen
```

---

## Dateistruktur

```
tools/
├── extract_text.py
├── create_language.py
├── inject_text.py
├── auto_translate.py
├── update_translation.py
├── stats.py
└── editor.html

translations/
├── en_source.json
├── de/
│   └── de.json
├── fr/
│   └── fr.json
└── ... (weitere Sprachen)

output/
└── (fertige .gba Dateien)
```

---

## Lizenz

MIT – [LICENSE](LICENSE)  
Übersetzungsdaten: CC BY-SA 4.0  
**Nur `.ups`-Patches verteilen, nie `.gba` – Copyright Nintendo/Game Freak**
