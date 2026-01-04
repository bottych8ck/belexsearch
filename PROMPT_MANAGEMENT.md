# Prompt Management System

Diese App verfügt über ein vollständiges System zur Verwaltung benutzerdefinierter System-Prompts.

## Features

### 1. Gespeicherte Prompts laden
- Im Tab **Promptengineering** finden Sie ein Dropdown-Menü mit allen gespeicherten System-Prompts
- Wählen Sie einen Prompt aus der Liste, um Details anzuzeigen
- Klicken Sie auf "Prompt in Editor laden", um ihn zu bearbeiten

### 2. Prompts bearbeiten
- Der Prompt-Editor zeigt den aktuell ausgewählten oder aktiven Prompt an
- Bearbeiten Sie den Prompt direkt im Textfeld
- Klicken Sie auf "✅ Anwenden", um den bearbeiteten Prompt für Ihre Suchen zu verwenden
- Klicken Sie auf "🔄 Standard", um zum Standard-Prompt zurückzukehren

### 3. Prompts speichern

#### Lokal speichern (empfohlen für Tests)
1. Klappen Sie den Bereich "Aktuellen Prompt speichern" auf
2. Geben Sie einen Namen, eine Beschreibung und Ihren Namen ein
3. Klicken Sie auf "💾 Lokal speichern"
4. Der Prompt wird in `saved_prompts.json` gespeichert

#### Via Git committen (empfohlen für dauerhafte Speicherung)
Nach dem lokalen Speichern:
```bash
git add saved_prompts.json
git commit -m "Add new system prompt: [Ihr Prompt-Name]"
git push
```

#### Via GitHub Actions (optional)
Verwenden Sie den GitHub Actions Workflow für automatisches Speichern:
1. Gehen Sie zu **Actions** → **Save System Prompt** in Ihrem GitHub Repository
2. Klicken Sie auf "Run workflow"
3. Füllen Sie die Felder aus:
   - **prompt_name**: Name des Prompts (z.B. "Studienrecht Assistent")
   - **prompt_description**: Kurze Beschreibung
   - **prompt_content**: Der vollständige Prompt-Text
   - **created_by**: Ihr Name oder Email
4. Klicken Sie auf "Run workflow"

Der Workflow wird automatisch:
- Die `saved_prompts.json` Datei aktualisieren
- Einen Commit erstellen
- Die Änderungen zum Repository pushen

## Dateistruktur

### saved_prompts.json
Enthält alle gespeicherten Prompts im folgenden Format:

```json
{
  "prompts": [
    {
      "name": "Prompt-Name",
      "description": "Beschreibung des Prompts",
      "prompt": "Der vollständige Prompt-Text...",
      "created_by": "Max Mustermann",
      "created_at": "2026-01-04T15:00:00Z"
    }
  ]
}
```

### .github/workflows/save_prompt.yml
GitHub Actions Workflow für automatisches Speichern von Prompts.

## Best Practices

1. **Aussagekräftige Namen**: Verwenden Sie beschreibende Namen für Ihre Prompts
   - ✅ "Detaillierte juristische Analyse"
   - ❌ "Prompt 1"

2. **Klare Beschreibungen**: Beschreiben Sie den Zweck des Prompts
   - ✅ "Fokussiert auf Studienrecht mit erweiterten Quellenangaben"
   - ❌ "Ein guter Prompt"

3. **Versionierung**: Bei größeren Änderungen erstellen Sie einen neuen Prompt statt den alten zu überschreiben
   - z.B. "Rechtsassistent v2.0" statt den existierenden "Rechtsassistent" zu ändern

4. **Testen**: Testen Sie neue Prompts ausgiebig, bevor Sie sie dauerhaft committen

5. **Dokumentation**: Nutzen Sie das Beschreibungsfeld, um Anwendungsfälle zu dokumentieren

## Sicherheit

- Die `saved_prompts.json` Datei wird im Git-Repository getrackt
- Achten Sie darauf, keine sensiblen Informationen in Prompts zu speichern
- Prompts sind für alle Repository-Mitglieder sichtbar

## Troubleshooting

**Problem**: Gespeicherte Prompts werden nicht angezeigt
- **Lösung**: Überprüfen Sie, ob `saved_prompts.json` existiert und gültiges JSON enthält

**Problem**: Fehler beim Speichern
- **Lösung**: Stellen Sie sicher, dass alle Pflichtfelder ausgefüllt sind

**Problem**: GitHub Actions Workflow schlägt fehl
- **Lösung**: Überprüfen Sie die Workflow-Logs im Actions-Tab
- Stellen Sie sicher, dass der Workflow Schreibrechte für das Repository hat

## Erweiterungen

Das System kann erweitert werden mit:
- Import/Export von Prompts als separate Dateien
- Prompt-Kategorien und Tags
- Bewertungssystem für Prompts
- Prompt-Vorlagen für verschiedene Rechtsgebiete
