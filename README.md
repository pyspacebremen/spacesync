# SpaceSync

Tkinter-Programm zum Übertragen zwischen ZIP-Archiv und Verzeichnis.

## Starten

Python 3.10 oder neuer mit Tkinter wird benötigt. Keine zusätzlichen Python-Pakete erforderlich.

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

## Sprache

Unter **Einstellungen → Sprache** stehen **Systemsprache**, **Deutsch**, **English** und **Nederlands** zur Verfügung. Die Auswahl wirkt sofort und wird in `spacesync.json` gespeichert. Ohne ausdrückliche Auswahl (`"language": ""`) wird die Systemsprache verwendet; nicht unterstützte Sprachen fallen auf Englisch zurück. Bereits vorhandene Protokollzeilen bleiben unverändert. Beschriftungen nativer Betriebssystemdialoge folgen den Systemeinstellungen.

Weitere Sprachen lassen sich ohne Python-Änderung in `languages.json` ergänzen:

1. Den gesamten Eintrag `en` kopieren und beispielsweise unter `fr` einfügen.
2. `name` auf den gewünschten Menünamen setzen, etwa `Français`.
3. Die Werte unter `messages` übersetzen. Schlüssel und Platzhalter wie `{archive}`, `{path}` oder `{error}` unverändert lassen.
4. Die JSON-Datei speichern und SpaceSync neu starten. Die neue Sprache erscheint automatisch im Menü.

Fehlende Übersetzungsschlüssel werden aus `en` übernommen. `languages.json` muss zusammen mit `spacesync.py` bereitgestellt werden.
