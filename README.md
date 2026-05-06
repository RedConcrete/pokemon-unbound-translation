# Pokémon Unbound – Translation Toolkit

Multi-language translation pipeline für Pokémon Unbound (GBA ROM-Hack).  
Workflow: ROM → Strings extrahieren → Übersetzen (Browser-Editor) → Zurückinjizieren.

---

## Voraussetzungen

- **Python 3.9+** – [python.org](https://www.python.org/downloads/)
- Ein gepatchtes **Pokémon Unbound .gba** (FireRed v1.0 + UPS-Patch via [Flips](https://github.com/Alcaro/Flips))
- Einen modernen Browser (für den Editor – kein Server nötig)
- Kein externes Tool, keine Libraries – alles reines Python + HTML

---

## Schnellstart

### 1. Text aus ROM extrahieren

```powershell
py tools/extract_text.py "Pokemon Unbound (v2.1.1.1).gba" --output translations/en_source.json
```

Dauert ca. 30–60 Sekunden. Fortschrittsbalken wird angezeigt.  
Ergebnis: `translations/en_source.json` – alle lesbaren Strings mit Offset + Länge.

> Nur einmal nötig, außer bei einer neuen Unbound-Version (siehe unten).

---

### 2. Sprachdatei erstellen

```powershell
# Deutsch
py tools/create_language.py translations/en_source.json translations/de/de.json

# Weitere Sprachen – gleiche Basis, anderer Ordner
py tools/create_language.py translations/en_source.json translations/fr/fr.json
py tools/create_language.py translations/en_source.json translations/es/es.json
py tools/create_language.py translations/en_source.json translations/it/it.json
```

Bestehende Übersetzungen werden beim erneuten Ausführen **nicht überschrieben** – bereits fertige Einträge bleiben erhalten.

---

### 3. Übersetzen im Browser-Editor

`tools/editor.html` direkt im Browser öffnen (Doppelklick reicht):

- **📂 JSON laden** → deine `de.json` wählen
- Englischen Text links lesen, Übersetzung rechts eingeben
- **✓ Fertig** klicken wenn ein Eintrag abgeschlossen ist
- Suchfeld + Filter **„Nur offen"** nutzen um fokussiert zu arbeiten
- **💾 JSON speichern** – lädt die aktualisierte Datei herunter
- Die heruntergeladene Datei nach `translations/de/de.json` kopieren (alte ersetzen)

> Tipp: Arbeite in Blöcken von 50–100 Strings. Speichere regelmäßig.  
> Der Fortschrittsbalken oben zeigt wie weit du bist.

---

### 4. Übersetzung testen (Dry-Run)

Vor dem Bauen prüfen ob Strings zu lang sind:

```powershell
py tools/inject_text.py "Pokemon Unbound (v2.1.1.1).gba" translations/de/de.json --dry-run
```

Zeigt alle Einträge die gekürzt werden müssen, ohne die ROM zu verändern.

---

### 5. ROM bauen

```powershell
py tools/inject_text.py "Pokemon Unbound (v2.1.1.1).gba" translations/de/de.json --output output/unbound_de.gba
```

→ `output/unbound_de.gba` direkt im Emulator (z.B. [mGBA](https://mgba.io/)) spielbar.

---

### 6. UPS-Patch erstellen (zum Verteilen)

```powershell
Flips.exe --create "Pokemon Unbound (v2.1.1.1).gba" output/unbound_de.gba output/unbound_de.ups
```

**Nur den `.ups`-Patch verteilen**, nie die fertige `.gba` – Copyright.  
Spieler patchen selbst: eigene FireRed-ROM + Original-Unbound-Patch + dein Sprach-Patch.

---

### 7. Fortschritt anzeigen

```powershell
py tools/stats.py
```

```
── Pokémon Unbound Translation Progress ──────────────────

  Deutsch 🇩🇪           ████████████░░░░░░░░░░░░░░░░░░  41%  (9.236/22.466)
  Français 🇫🇷           ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   0%  (0/22.466)
```

---

### 8. Auf GitHub pushen

```powershell
git add translations/de/de.json
git commit -m "DE: 500 Strings übersetzt – Story Akt 1 fertig"
git push
```

> Die `.gba` Datei **nicht** committen – sie ist in `.gitignore` ausgeschlossen.

---

## Neue Unbound-Version mergen

Wenn Skeli eine neue Version released:

```powershell
# 1. Neue ROM extrahieren
py tools/extract_text.py "Pokemon Unbound (v2.2).gba" --output translations/en_source_new.json

# 2. Übersetzung mergen – behält alles was schon fertig ist
py tools/update_translation.py translations/en_source.json translations/en_source_new.json translations/de/de.json

# 3. Alten Source ersetzen
copy translations\en_source_new.json translations\en_source.json

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
py tools/create_language.py translations/en_source.json translations/fr/fr.json
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
unbound-translation-toolkit/
├── .gitignore
├── README.md
├── tools/
│   ├── extract_text.py       ← Text aus ROM extrahieren
│   ├── create_language.py    ← Neue Sprache anlegen
│   ├── inject_text.py        ← Übersetzung ins ROM schreiben
│   ├── update_translation.py ← Neue ROM-Version mergen
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
    ▼  py tools/extract_text.py
translations/en_source.json
    │
    ▼  py tools/create_language.py
translations/de/de.json  (leer)
    │
    ▼  tools/editor.html im Browser
translations/de/de.json  (übersetzt)
    │
    ▼  py tools/inject_text.py --dry-run
Längen prüfen, ggf. kürzen
    │
    ▼  py tools/inject_text.py
output/unbound_de.gba  →  Emulator testen
    │
    ▼  Flips.exe --create
output/unbound_de.ups  ←  verteilen
    │
    ▼  git push
github.com/RedConcrete/pokemon-unbound-translation
```

---

## Alle Befehle auf einen Blick

```powershell
# Einmalig: extrahieren + Sprachdatei erstellen
py tools/extract_text.py "Pokemon Unbound (v2.1.1.1).gba" --output translations/en_source.json
py tools/create_language.py translations/en_source.json translations/de/de.json

# Wiederholt: testen + ROM bauen
py tools/inject_text.py "Pokemon Unbound (v2.1.1.1).gba" translations/de/de.json --dry-run
py tools/inject_text.py "Pokemon Unbound (v2.1.1.1).gba" translations/de/de.json --output output/unbound_de.gba

# Fortschritt
py tools/stats.py

# GitHub
git add translations/de/de.json
git commit -m "DE: X Strings übersetzt"
git push

# Neue Unbound-Version
py tools/extract_text.py "Pokemon Unbound (v2.2).gba" --output translations/en_source_new.json
py tools/update_translation.py translations/en_source.json translations/en_source_new.json translations/de/de.json
copy translations\en_source_new.json translations\en_source.json

# Neue Sprache
py tools/create_language.py translations/en_source.json translations/fr/fr.json
```