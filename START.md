# MailToLLM - Startanleitung

## Voraussetzungen

```bash
# Python 3.10 oder höher erforderlich
python3 --version

# Abhängigkeiten installieren
pip install -e .
```

## App starten

### Methode 1: Mit dem run.py Script (empfohlen)

```bash
python3 run.py
```

Oder direkt ausführbar machen:
```bash
chmod +x run.py
./run.py
```

### Methode 2: Als Python-Modul (nach Installation)

```bash
# Erst installieren
pip install -e .

# Dann starten
python3 -m mailtollm.ui.app
```

### Methode 3: Aus dem src-Verzeichnis

```bash
cd src
python3 -m mailtollm.ui.app
```

## Icon

Die App zeigt automatisch das MailToLLM-Icon:
- **Im Fenster**: Das Icon wird in der Titelleiste angezeigt
- **Im Dock**: Beim Starten erscheint das Icon im macOS Dock

Icon-Dateien befinden sich in:
- `src/mailtollm/resources/icon.png` - Fenster-Icon
- `src/mailtollm/resources/icon.icns` - macOS App Bundle Icon

## Icon neu generieren

Falls du das Icon anpassen möchtest:

```bash
python3 scripts/create_icon.py
```

Dies erstellt:
1. PNG-Icon für das Fenster
2. Alle Icon-Größen für macOS (16x16 bis 1024x1024)
3. Die .icns Datei für App-Bundles

## Eigenständige App erstellen (optional)

Um eine richtige macOS .app zu erstellen:

```bash
# PyInstaller installieren
pip install pyinstaller

# App Bundle erstellen
pyinstaller --name="MailToLLM" \
  --icon="src/mailtollm/resources/icon.icns" \
  --windowed \
  --onefile \
  run.py

# Die App befindet sich dann in dist/MailToLLM.app
```

Oder mit py2app:

```bash
# py2app installieren
pip install py2app

# Setup-Datei erstellen und App bauen
python3 setup.py py2app
```

## Troubleshooting

**Problem**: "ModuleNotFoundError: No module named 'mailtollm'"

**Lösung**: Verwende `run.py` statt direktem Modulimport, oder installiere das Package mit `pip install -e .`

**Problem**: Icon wird nicht angezeigt

**Lösung**:
1. Prüfe ob die Icon-Dateien existieren: `ls -la src/mailtollm/resources/`
2. Generiere Icons neu: `python3 scripts/create_icon.py`
3. Stelle sicher, dass PIL installiert ist: `pip install Pillow`
