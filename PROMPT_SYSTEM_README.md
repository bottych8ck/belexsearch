# Prompt Management System - Schnellstart

## ✅ Was wurde implementiert?

Ein vollständiges System zum Speichern, Verwalten und Teilen von benutzerdefinierten System-Prompts.

## 🎯 Hauptfunktionen

1. **Prompts auswählen** - Dropdown mit allen gespeicherten Prompts
2. **Prompts laden** - In den Editor laden und bearbeiten
3. **Prompts speichern** - Lokal oder via GitHub Actions
4. **Prompts löschen** - Ungewollte Prompts entfernen
5. **Prompts teilen** - Via Git mit anderen Nutzern teilen

## 📁 Neue Dateien

```
BELEX/
├── saved_prompts.json              # Speichert alle Prompts
├── .github/
│   └── workflows/
│       └── save_prompt.yml         # GitHub Actions Workflow
├── PROMPT_MANAGEMENT.md            # Vollständige Dokumentation
├── GITHUB_SETUP.md                 # GitHub-Konfiguration
└── app_unibe.py                    # Erweiterte App (GEÄNDERT)
```

## 🚀 Schnellstart

### In der App verwenden

1. Öffnen Sie die App und gehen Sie zum Tab **"Promptengineering"**
2. Wenn Prompts gespeichert sind, erscheint ein Dropdown
3. Wählen Sie einen Prompt → Klicken Sie "📥 Prompt in Editor laden"
4. Bearbeiten Sie den Prompt nach Belieben
5. Klicken Sie "✅ Anwenden" um ihn zu verwenden

### Neuen Prompt speichern

1. Bearbeiten Sie den Prompt im Editor
2. Klappen Sie "Aktuellen Prompt speichern" auf
3. Füllen Sie alle Felder aus:
   - Name (z.B. "Detaillierte Rechtsanalyse")
   - Beschreibung (z.B. "Gibt sehr ausführliche Antworten mit vielen Quellen")
   - Ihr Name/Email
4. Klicken Sie "💾 Lokal speichern"
5. **Wichtig**: Committen Sie die Änderungen:
   ```bash
   git add saved_prompts.json
   git commit -m "Add prompt: [Name]"
   git push
   ```

### Prompt löschen

1. Wählen Sie den Prompt im Dropdown aus
2. Klicken Sie auf "🗑️ Löschen"
3. Committen Sie die Löschung mit Git

## 🔑 GitHub Actions - Keine Keys erforderlich!

**Gute Nachricht**: Sie müssen **KEINE** GitHub-Keys oder Secrets erstellen!

Der Workflow funktioniert automatisch mit dem von GitHub bereitgestellten `GITHUB_TOKEN`.

### Einzige mögliche Anpassung

Falls der Workflow nicht funktioniert:
1. GitHub → Repository → **Settings** → **Actions** → **General**
2. Bei "Workflow permissions": Wählen Sie **"Read and write permissions"**
3. Speichern

Mehr Details: Siehe `GITHUB_SETUP.md`

## 📚 Dokumentation

- **PROMPT_MANAGEMENT.md** - Vollständige Anleitung mit Best Practices
- **GITHUB_SETUP.md** - GitHub Actions Konfiguration und Troubleshooting
- **PROMPT_SYSTEM_README.md** - Diese Datei (Schnellübersicht)

## 🔄 Workflow-Beispiele

### Beispiel 1: Lokales Speichern

```bash
# 1. In der App: Prompt bearbeiten und "Lokal speichern" klicken
# 2. Im Terminal:
cd C:\Users\Phili\Documents\Programmieren\BELEX
git add saved_prompts.json
git commit -m "Add prompt: Studienrecht fokussiert"
git push origin unibe-version
```

### Beispiel 2: Via GitHub Actions

1. Gehen Sie zu: `https://github.com/[IHR-USER]/[IHR-REPO]/actions/workflows/save_prompt.yml`
2. Klicken Sie "Run workflow"
3. Füllen Sie das Formular aus
4. Workflow speichert automatisch und committed

## ⚡ Tipps

1. **Standard-Prompt nicht löschen**: Der erste Prompt sollte als Vorlage bleiben
2. **Aussagekräftige Namen**: "Kurze Antworten" statt "Prompt1"
3. **Beschreibungen nutzen**: Helfen anderen Nutzern den richtigen Prompt zu finden
4. **Versionierung**: Bei großen Änderungen neuen Prompt erstellen (v2, v3)
5. **Testen**: Testen Sie neue Prompts bevor Sie sie committen

## 🆘 Häufige Probleme

| Problem | Lösung |
|---------|--------|
| Prompts werden nicht geladen | Prüfen Sie ob `saved_prompts.json` existiert |
| Fehler beim Speichern | Alle Pflichtfelder ausfüllen |
| GitHub Actions funktioniert nicht | Workflow-Permissions prüfen (siehe GITHUB_SETUP.md) |
| Prompt wurde nicht gelöscht | Nach Löschen mit Git committen |

## 📞 Support

Bei Fragen:
1. Lesen Sie `PROMPT_MANAGEMENT.md` für Details
2. Lesen Sie `GITHUB_SETUP.md` für GitHub-spezifische Probleme
3. Prüfen Sie die Workflow-Logs im Actions-Tab

---

**Entwickelt für die Universität Bern** | kueblaw.ch
