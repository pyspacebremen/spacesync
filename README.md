# SpaceSync

Tkinter-Programm zum Übertragen zwischen ZIP-Archiv und Verzeichnis.

## Starten

Python 3.10 oder neuer mit Tkinter wird benötigt. Für den optionalen PDF-Export zusätzlich ReportLab installieren:

```sh
python3 -m pip install -r requirements.txt
```

```sh
python3 spacesync.py
```

- Oben den Pfad eines vorhandenen oder neuen ZIP-Archivs eingeben bzw. auswählen.
- Unten das Zielverzeichnis eingeben bzw. auswählen (beim Archivieren dient es als Quelle).
- **↑ Archiv erstellen / ersetzen** schreibt den gesamten Verzeichnisinhalt einschließlich leerer Verzeichnisse in ein neues ZIP-Archiv. Ein bestehendes Archiv wird nach Bestätigung vollständig ersetzt.
- **↓ Archiv entpacken** entpackt das Archiv und überschreibt gleichnamige Dateien. Zusätzliche Dateien bleiben erhalten.
- **Ziel vor dem Entpacken vollständig leeren** entfernt nach Bestätigung alle bisherigen Inhalte des Zielverzeichnisses.
- Rechts erscheinen Aktionen und Fehler. Die Oberfläche bleibt während der Verarbeitung bedienbar.

Beide Pfadfelder und die Option zum Leeren werden automatisch nach Änderungen und beim Schließen in `spacesync.json` neben dem Python-Programm gespeichert und beim Start wiederhergestellt. Die Datei wird beim ersten Speichern angelegt; das Programmverzeichnis muss beschreibbar sein. Lade- und Speicherfehler erscheinen im Meldungsfenster. Die Bestätigung vor dem Leeren bleibt auch bei gespeicherter Option erforderlich.

Das Archiv muss außerhalb des ausgewählten Verzeichnisses liegen. Symbolische Links werden nicht unterstützt. Archive werden vor dem Verändern des Ziels vollständig in ein temporäres Verzeichnis entpackt und dabei auf ungültige Pfade geprüft. Beim anschließenden Kopieren können etwa bei Speicherplatzmangel bereits Teile des Ziels verändert worden sein.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

## Bedienungsanleitung und PDF

**Hilfe → Bedienungsanleitung** öffnet eine scrollbare Anleitung in der aktuell ausgewählten Sprache. Der Dialog erklärt Pfade, Archivieren, Entpacken, die Leerungsoption sowie Einstellungen und Fehlermeldungen. Über **Als PDF exportieren …** lässt sich dieselbe Beschreibung mit frei wählbarem Dateinamen und Speicherort als PDF speichern. Ohne ReportLab bleiben Anwendung und Hilfe nutzbar; beim Export erscheint ein Installationshinweis.

Die Texte der Anleitung stehen ebenfalls in `languages.json` unter den Schlüsseln `manual_*` und können dort für weitere Sprachen übersetzt werden.

## Sprache

Unter **Einstellungen → Sprache** stehen **Systemsprache**, **Deutsch**, **English** und **Nederlands** zur Verfügung. Die Auswahl wirkt sofort und wird in `spacesync.json` gespeichert. Ohne ausdrückliche Auswahl (`"language": ""`) wird die Systemsprache verwendet; nicht unterstützte Sprachen fallen auf Englisch zurück. Bereits vorhandene Protokollzeilen bleiben unverändert. Beschriftungen nativer Betriebssystemdialoge folgen den Systemeinstellungen.

Weitere Sprachen lassen sich ohne Python-Änderung in `languages.json` ergänzen:

1. Den gesamten Eintrag `en` kopieren und beispielsweise unter `fr` einfügen.
2. `name` auf den gewünschten Menünamen setzen, etwa `Français`.
3. Die Werte unter `messages` übersetzen. Schlüssel und Platzhalter wie `{archive}`, `{path}` oder `{error}` unverändert lassen.
4. Die JSON-Datei speichern und SpaceSync neu starten. Die neue Sprache erscheint automatisch im Menü.

Fehlende Übersetzungsschlüssel werden aus `en` übernommen. `languages.json` muss zusammen mit `spacesync.py` bereitgestellt werden.

## Kommandozeile / Headless

Ohne Argumente öffnet sich die grafische Oberfläche. Mit einer Aktion läuft SpaceSync ohne Fenster und ohne Tkinter. Alle nicht angegebenen Einstellungen werden aus `spacesync.json` neben dem Programm übernommen.

```sh
# Mit den gespeicherten Pfaden archivieren bzw. entpacken
python3 spacesync.py archive
python3 spacesync.py extract

# Pfade ausdrücklich setzen
python3 spacesync.py archive --archive /backup/daten.zip --directory /daten

# Ziel überschreiben und gespeichertes Leeren ausdrücklich abschalten
python3 spacesync.py extract --directory /ziel --no-clear

# Alternative Konfiguration, Ziel leeren und Einstellungen danach speichern
python3 spacesync.py extract --config /pfad/settings.json --clear --save-settings

# Anleitung anzeigen oder als PDF exportieren
python3 spacesync.py manual --language de
python3 spacesync.py manual --language nl --pdf handleiding.pdf

python3 spacesync.py --help
```

| Parameter | Bedeutung |
| --- | --- |
| `archive`, `create` | Verzeichnis als ZIP archivieren; beide Namen sind gleichwertig |
| `extract`, `unpack` | ZIP ins Zielverzeichnis entpacken; beide Namen sind gleichwertig |
| `manual` | Anleitung im Terminal ausgeben; mit `--pdf` exportieren |
| `-a`, `--archive PFAD` | ZIP-Archiv; sonst `archive` aus JSON |
| `-d`, `--directory PFAD` | Quell-/Zielverzeichnis; sonst `directory` aus JSON |
| `--clear` / `--no-clear` | Leeren aktivieren/deaktivieren; sonst `clear` aus JSON |
| `--language CODE` | Zum Beispiel `de`, `en`, `nl` oder `system`; sonst `language` aus JSON |
| `--config DATEI` | Andere JSON-Datei verwenden |
| `--save-settings` | Aufgelöste Einstellungen nach erfolgreicher Ausführung in die gewählte Konfiguration schreiben |
| `--headless` | Optional; mit einer Aktion ist Headless ohnehin aktiv |
| `--pdf DATEI` | PDF-Zieldatei für `manual`; benötigt ReportLab |
| `-h`, `--help` | Parameterübersicht anzeigen |

**CLI-Werte haben Vorrang vor JSON-Werten.** Eine fehlende JSON-Datei entspricht leeren Pfaden, `clear=false` und Systemsprache. Fehlen danach erforderliche Pfade, wird mit einer Fehlermeldung abgebrochen. Fehlerhaftes JSON wird als Fehler gemeldet. CLI-Aufrufe speichern Einstellungen ausschließlich mit `--save-settings`.

**Im CLI gibt es keine Sicherheitsrückfragen:** `archive` ersetzt bestehende Archive, `extract` überschreibt gleichnamige Dateien. `--clear` oder ein gespeichertes `clear=true` löscht alle bisherigen Zielinhalte. Mit `--no-clear` kann dies ausdrücklich unterbunden werden.

Relative Pfade (auch aus der Konfiguration) beziehen sich auf das aktuelle Arbeitsverzeichnis. `~` am Pfadanfang wird zum Benutzerverzeichnis erweitert. Pfade mit Leerzeichen müssen in Anführungszeichen stehen.

Aktionen erscheinen auf der Standardausgabe, Fehler auf der Standardfehlerausgabe. Exitcodes: **0** erfolgreich, **1** Ausführungs- oder Konfigurationsfehler, **2** ungültiger Aufruf.

Die Tkinter-Oberfläche liegt in `spacesync_gui.py` und wird erst beim Start ohne Argumente geladen. Beim Weitergeben der Anwendung diese Datei ebenfalls mitliefern.
