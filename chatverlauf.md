# Chatverlauf – SpaceSync

## 1. Tkinter-Programm erstellen

### Benutzer · 19:21

Erzeuge ein Python Programm mit Tkinter, das mit zwei Eingeabefeldern ausgestattet ist. In dem ersten Feld kann ein Pfad uu einem Zip-Archiv eingegeben werden. Im Feld darunter Das Zielverzeichnis, in dem das Zip-Archiv entpackt bzw. sysnchronisiert wird.

Zwischen den beiden Feldern sind zwei Button anzuorden die jeweils einen Pfeil nach und nach unten zeigen und eine entprechende Funktion ausführen um die Dateien und Verzeichnisse des Zielverzeichnises in das Archiv zu schreiben bzw. ein Archiv zu erzeugen. Dire andrere Richtung soll den Inhalt des Archives in das Zielverzeichnis entpacken.

Eine Option kann vorher das Zielverzeichnis leeren. Daneben soll ein Meldungsfenster Felhlermeldung und Aktionen ausgeben.

### Assistent · 19:22

*Dauer: 48 Sek.*

Das Programm ist in [spacesync.py](spacesync.py) erstellt.

- Zwei Pfadfelder mit Dateiauswahl
- ↑ Verzeichnis als ZIP speichern
- ↓ ZIP ins Zielverzeichnis entpacken
- Optionales Leeren mit Sicherheitsabfrage
- Protokoll für Aktionen und Fehler

Starten mit:

```sh
python3 spacesync.py
```

Alle drei Funktionstests bestehen. Das grafische Fenster konnte in dieser Ausführungsumgebung nicht erfolgreich gestartet werden. Hinweise stehen in der [README.md](README.md).

## 2. Einstellungen in JSON speichern

### Benutzer · 19:51

Eingabefelder und Optionen sollen persistiert werden in einer json Datei

### Assistent · 19:52

*Dauer: 19 Sek.*

Beide Pfadfelder und die Option „Ziel leeren“ werden automatisch in `spacesync.json` neben dem Programm gespeichert und beim nächsten Start wiederhergestellt.

Lade- und Speicherfehler erscheinen im Meldungsfenster. Die JSON-Datei ist von Git ausgeschlossen.

Alle fünf Tests bestehen.

#### Angezeigte Dateiänderungen

4 Dateien bearbeitet: **+90 / −1**.

| Datei | Hinzugefügt | Entfernt |
| --- | ---: | ---: |
| `.gitignore` | 1 | 0 |
| `README.md` | 2 | 0 |
| `spacesync.py` | 64 | 0 |

*Eine weitere Datei war in der kopierten Ansicht ausgeblendet.*

## 3. Sprachumschaltung hinzufügen

### Benutzer · 19:57

Einstellungsmenü item für Sprachumschaltung Englisch und Deutsch. Wenn keine Sprache gewählt wird, soll die im System eingestellte Sprache benutzt werden. Eine weiter Sprache soll durch erweitern einer json Datei einfach möglich sein.

### Assistent · 19:58

*Dauer: 1 Min. 15 Sek.*

Umgesetzt:

- **Einstellungen → Sprache** mit Systemsprache, Deutsch und Englisch.
- Umschaltung wirkt sofort und wird gespeichert.
- Ohne Auswahl wird die Systemsprache verwendet, ersatzweise Englisch.
- Weitere Sprachen können in [languages.json](languages.json) ergänzt werden. Anleitung steht in der README.

Alle acht Tests bestehen. Die grafische Oberfläche wurde hier nicht erneut gestartet.

#### Angezeigte Dateiänderungen

2 Dateien bearbeitet: **+90 / −2**.

| Datei | Hinzugefügt | Entfernt |
| --- | ---: | ---: |
| `spacesync.py` | 54 | 1 |
| `tests/test_spacesync.py` | 36 | 1 |

## 4. Niederländisch ergänzen

### Benutzer · 20:00

Füge niederländisch hinzu

### Assistent · 20:01

*Dauer: 12 Sek.*

Niederländisch ist vollständig ergänzt. Nach einem Neustart erscheint **Nederlands** unter **Einstellungen → Sprache**.

Alle acht Tests bestehen, einschließlich der Prüfung aller Übersetzungsschlüssel und Platzhalter.
