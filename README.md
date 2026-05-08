# Pokémon Unbound – Translation Toolkit

Multi-language translation pipeline für Pokémon Unbound (GBA ROM-Hack).  
Workflow: ROM → Strings extrahieren → Übersetzen (Browser-Editor + KI-Hilfe) → Zurückinjizieren.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Fortschritt DE](https://img.shields.io/badge/Deutsch-41%25-yellow)
![Lizenz](https://img.shields.io/badge/Lizenz-MIT-green)

---

## Voraussetzungen

- **Python 3.9+** – [python.org](https://www.python.org/downloads/)
- Ein gepatchtes **Pokémon Unbound .gba** (FireRed v1.0 + UPS-Patch via [Flips](https://github.com/Alcaro/Flips))
- Einen modernen Browser (für den Editor – kein Server nötig)
- Kein externes Tool, keine Libraries – alles reines Python + HTML
- Optional für KI-Übersetzung: `pip install anthropic` + Anthropic API Key

> **Plattformhinweis:** Unter Windows lautet der Python-Befehl `py`, unter Linux/macOS `python3`.  
> Alle Beispiele unten zeigen beide Varianten.

---

## Schnellstart

### 1. Text aus ROM extrahieren

```powershell
# Windows
py tools/extract_text.py "Pokemon Unbound (v2.1.1.1).gba" --output translations/en_source.json

# Linux / macOS
python3 tools/extract_text.py "Pokemon Unbound (v2.1.1.1).gba" --output translations/en_source.json
```

Dauert ca. 30–60 Sekunden. Fortschrittsbalken wird angezeigt.  
Ergebnis: `translations/en_source.json` – alle lesbaren Strings mit Offset + Länge.

> Nur einmal nötig, außer bei einer neuen Unbound-Version (siehe unten).

---

### 2. Sprachdatei erstellen

```powershell
# Windows
py tools/create_language.py translations/en_source.json translations/de/de.json

# Linux / macOS
python3 tools/create_language.py translations/en_source.json translations/de/de.json
```

Für weitere Sprachen denselben Befehl mit anderem Pfad wiederholen (`fr/fr.json`, `es/es.json`, …).

Bestehende Übersetzungen werden beim erneuten Ausführen **nicht überschrieben** – bereits fertige Einträge bleiben erhalten.

---

### 3. Übersetzen im Browser-Editor

`tools/editor.html` direkt im Browser öffnen (Doppelklick reicht):

- **📂 JSON laden** → deine `de.json` wählen
- Englischen Text links lesen, Übersetzung rechts eingeben
- **✓ Fertig** klicken wenn ein Eintrag abgeschlossen ist
- Suchfeld + Filter nutzen um fokussiert zu arbeiten:
  - **Nur offen** – noch nicht übersetzte Einträge
  - **🤖 KI – zu prüfen** – KI-übersetzte Einträge, die manuell geprüft werden müssen
- **💾 JSON speichern** – lädt die aktualisierte Datei herunter
- Die heruntergeladene Datei nach `translations/de/de.json` kopieren (alte ersetzen)

> Tipp: Arbeite in Blöcken von 50–100 Strings. Speichere regelmäßig.  
> Der Fortschrittsbalken oben zeigt wie weit du bist.

---

### 4. (Optional) KI-Vorabübersetzung

Kurze, repetitive Strings (Item-Namen, Attacken, UI-Texte) lassen sich per Claude-API automatisch vorübersetzen.

**Setup:**
```powershell
pip install anthropic

# Windows (PowerShell)
$env:ANTHROPIC_API_KEY = "sk-ant-..."

# Linux / macOS
export ANTHROPIC_API_KEY="sk-ant-..."
```

**Verwendung:**
```powershell
# Nur kurze Strings übersetzen (empfohlen als Einstieg)
python3 tools/auto_translate.py translations/de/de.json --max-length 30

# Strings die einen bestimmten Text enthalten (z.B. Pokémon-Namen)
python3 tools/auto_translate.py translations/de/de.json --filter "Bulbasaur"

# Dry-Run – zeigt Kandidaten ohne API-Aufruf
python3 tools/auto_translate.py translations/de/de.json --max-length 30 --dry-run

# Alle unübersetzten Strings (Vorsicht – kostet API-Tokens!)
python3 tools/auto_translate.py translations/de/de.json --all
```

KI-übersetzte Einträge werden mit `[KI]` markiert und im Editor lila hervorgehoben.  
Im Editor-Filter **„🤖 KI – zu prüfen"** alle KI-Einträge aufrufen und manuell prüfen.

> **Geeignet für:** Item-Namen, Attacken, kurze UI-Strings  
> **Nicht geeignet für:** lange Story-Dialoge, Strings mit vielen Control-Codes  
> KI-Übersetzungen sind ein Startpunkt, kein Endprodukt – immer im Editor nachprüfen.

---

### 5. Übersetzung testen (Dry-Run)

Vor dem Bauen prüfen ob Strings zu lang sind:

```powershell
# Windows
py tools/inject_text.py "Pokemon Unbound (v2.1.1.1).gba" translations/de/de.json --dry-run

# Linux / macOS
python3 tools/inject_text.py "Pokemon Unbound (v2.1.1.1).gba" translations/de/de.json --dry-run
```

Zeigt alle Einträge die gekürzt werden müssen, ohne die ROM zu verändern.

---

### 6. ROM bauen

```powershell
# Windows
py tools/inject_text.py "Pokemon Unbound (v2.1.1.1).gba" translations/de/de.json --output output/unbound_de.gba

# Linux / macOS
python3 tools/inject_text.py "Pokemon Unbound (v2.1.1.1).gba" translations/de/de.json --output output/unbound_de.gba
```

→ `output/unbound_de.gba` direkt im Emulator (z.B. [mGBA](https://mgba.io/)) spielbar.

---

### 7. UPS-Patch erstellen (zum Verteilen)

```powershell
# Windows
Flips.exe --create "Pokemon Unbound (v2.1.1.1).gba" output/unbound_de.gba output/unbound_de.ups

# Linux / macOS (Flips als CLI bauen: https://github.com/Alcaro/Flips)
./flips --create "Pokemon Unbound (v2.1.1.1).gba" output/unbound_de.gba output/unbound_de.ups
```

**Nur den `.ups`-Patch verteilen**, nie die fertige `.gba` – Copyright.  
Spieler patchen selbst: eigene FireRed-ROM + Original-Unbound-Patch + dein Sprach-Patch.

---

### 8. Fortschritt anzeigen

```powershell
# Windows
py tools/stats.py

# Linux / macOS
python3 tools/stats.py
```

```
── Pokémon Unbound Translation Progress ──────────────────

  Deutsch 🇩🇪           ████████████░░░░░░░░░░░░░░░░░░  41%  (9.236/22.466)
  Français 🇫🇷           ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   0%  (0/22.466)
```

---

## Neue Unbound-Version mergen

Wenn Skeli eine neue Version released:

```powershell
# 1. Neue ROM extrahieren
python3 tools/extract_text.py "Pokemon Unbound (v2.2).gba" --output translations/en_source_new.json

# 2. Übersetzung mergen – behält alles was schon fertig ist
python3 tools/update_translation.py translations/en_source.json translations/en_source_new.json translations/de/de.json

# 3. Alten Source ersetzen
# Windows:
copy translations\en_source_new.json translations\en_source.json
# Linux / macOS:
cp translations/en_source_new.json translations/en_source.json

# 4. Editor öffnen → nur neue/geänderte Einträge übersetzen
```

Das Merge-Skript markiert automatisch:
- `⚡ NEU` – neue Strings, müssen übersetzt werden
- `⚠ GEÄNDERT` – englischer Text hat sich geändert, alte DE-Übersetzung als Notiz gespeichert
- Alles andere bleibt unberührt

Ein detaillierter Report wird in `translations/de/` gespeichert.

---

## Weitere Sprache hinzufügen

```powershell
python3 tools/create_language.py translations/en_source.json translations/fr/fr.json
```

Editor öffnen, `fr.json` laden, übersetzen. Keine Code-Änderungen nötig.  
Alle Sprachen teilen dieselbe Basis (`en_source.json`).

---

## Bekannte Einschränkungen

### Stringlänge
GBA-ROMs haben **fixe Speicherbereiche**. Eine Übersetzung darf **nicht länger** (in Bytes) sein als der Original-String. Deutsch ist oft 20–30% länger → kürzen nötig.

**Kürzungs-Tricks:**

| Englisch | Deutsch (zu lang) | Deutsch (ok) |
|----------|-------------------|--------------|
| `You received` | `Du hast erhalten` | `Erhalten:` |
| `Do you want to` | `Möchtest du` | `Willst du` |
| `Pokémon Trainer` | `Pokémon-Trainer` | `Trainer` |
| `Press A to continue` | `Drücke A um fortzufahren` | `A: Weiter` |
| `It's super effective!` | `Es ist sehr effektiv!` | `Sehr effektiv!` |
| `What will you do?` | `Was wirst du tun?` | `Was tun?` |

`--dry-run` zeigt alle zu langen Strings vor der Injektion an.

### Sonderzeichen (ä ö ü Ä Ö Ü ß)
Der Standard-FireRed-Charset unterstützt `äöüÄÖÜß` nicht.  
Unbound nutzt CFRU mit erweitertem Charset – teste im Emulator ob `ä` korrekt angezeigt wird.  
Wenn nicht, folgende Fallbacks verwenden:

| Zeichen | Fallback |
|---------|----------|
| `ä` | `ae` |
| `ö` | `oe` |
| `ü` | `ue` |
| `Ä` | `Ae` |
| `Ö` | `Oe` |
| `Ü` | `Ue` |
| `ß` | `ss` |

> Das `auto_translate.py`-Skript verwendet automatisch die Fallbacks.

### Control Codes
Alle Control-Codes aus dem Original beibehalten:

| Code | Bedeutung |
|------|-----------|
| `\n` | Zeilenumbruch (neue Zeile, selbe Textbox) |
| `\p` | Seitenumbruch (neue Textbox, Spieler drückt A) |
| `{PLAYER}` | Name des Spielers |
| `{RIVAL}` | Name des Rivals |
| `{COLOR}` | Textfarbe |
| `{SHADOW}` | Textschatten |
| `{HIGHLIGHT}` | Texthervorhebung |

**Beispiel:**
```
EN: Hello, {PLAYER}!\pAre you ready?
DE: Hallo, {PLAYER}!\pBist du bereit?
```

### Abgeschnittene Strings
Manche Strings im Editor beginnen mitten im Wort (z.B. `mon Unbound!` statt `Pokémon Unbound!`).  
Das sind Extraktionsfehler – einfach überspringen oder als Kommentar markieren.

---

## Dateistruktur

```
pokemon-unbound-translation/
├── .gitignore
├── README.md
├── tools/
│   ├── extract_text.py       ← Text aus ROM extrahieren
│   ├── create_language.py    ← Neue Sprache anlegen
│   ├── inject_text.py        ← Übersetzung ins ROM schreiben
│   ├── update_translation.py ← Neue ROM-Version mergen
│   ├── auto_translate.py     ← KI-Vorabübersetzung (Claude API)
│   ├── stats.py              ← Fortschritt aller Sprachen anzeigen
│   └── editor.html           ← Browser-Editor (kein Server nötig)
├── translations/
│   ├── en_source.json        ← Extrahierte Englisch-Quelle (NICHT editieren)
│   ├── de/
│   │   └── de.json
│   ├── fr/
│   │   └── fr.json
│   └── es/
│       └── es.json
└── output/                   ← Fertige ROMs (in .gitignore)
```

---

## Vollständiger Workflow

```
ROM (.gba)
    │
    ▼  python3 tools/extract_text.py
translations/en_source.json
    │
    ▼  python3 tools/create_language.py
translations/de/de.json  (leer)
    │
    ▼  (optional) python3 tools/auto_translate.py --max-length 30
translations/de/de.json  (KI-vorübersetzt, zum Prüfen markiert)
    │
    ▼  tools/editor.html im Browser
translations/de/de.json  (übersetzt + KI-Einträge geprüft)
    │
    ▼  python3 tools/inject_text.py --dry-run
Längen prüfen, ggf. kürzen
    │
    ▼  python3 tools/inject_text.py
output/unbound_de.gba  →  Emulator testen
    │
    ▼  flips --create
output/unbound_de.ups  ←  verteilen
```

---

## Alle Befehle auf einen Blick

```bash
# Einmalig: extrahieren + Sprachdatei erstellen
python3 tools/extract_text.py "Pokemon Unbound (v2.1.1.1).gba" --output translations/en_source.json
python3 tools/create_language.py translations/en_source.json translations/de/de.json

# Optional: KI-Vorabübersetzung kurzer Strings
export ANTHROPIC_API_KEY="sk-ant-..."
python3 tools/auto_translate.py translations/de/de.json --max-length 30

# Wiederholt: testen + ROM bauen
python3 tools/inject_text.py "Pokemon Unbound (v2.1.1.1).gba" translations/de/de.json --dry-run
python3 tools/inject_text.py "Pokemon Unbound (v2.1.1.1).gba" translations/de/de.json --output output/unbound_de.gba

# Fortschritt
python3 tools/stats.py

# Neue Unbound-Version
python3 tools/extract_text.py "Pokemon Unbound (v2.2).gba" --output translations/en_source_new.json
python3 tools/update_translation.py translations/en_source.json translations/en_source_new.json translations/de/de.json
cp translations/en_source_new.json translations/en_source.json

# Neue Sprache
python3 tools/create_language.py translations/en_source.json translations/fr/fr.json
```

---

## Mitmachen

Alle Sprachen willkommen! So startest du:

1. Repo forken
2. `python3 tools/create_language.py translations/en_source.json translations/XX/XX.json`
3. Im Editor übersetzen
4. Pull Request erstellen

Aktueller Status der Sprachen: `python3 tools/stats.py`

---

## Lizenz

MIT – siehe [LICENSE](LICENSE).  
Die Übersetzungsdaten (`translations/`) stehen unter CC BY-SA 4.0.  
**Keine `.gba`-Dateien committen oder verteilen** – nur `.ups`-Patches (Copyright Nintendo / Game Freak).
