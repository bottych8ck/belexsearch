# GitHub Actions Setup für Prompt-Speicherung

## Kurzantwort: Keine zusätzlichen Secrets erforderlich! 🎉

Der GitHub Actions Workflow für das Speichern von Prompts funktioniert **out of the box** ohne zusätzliche Konfiguration. GitHub stellt automatisch das `GITHUB_TOKEN` zur Verfügung.

## Wie es funktioniert

### Automatische Berechtigungen

Der Workflow verwendet bereits die korrekten Berechtigungen:

```yaml
permissions:
  contents: write
```

Diese Zeile im Workflow gibt GitHub Actions die Berechtigung, Änderungen am Repository vorzunehmen (Dateien zu ändern und zu committen).

### Das GITHUB_TOKEN

- Wird **automatisch** von GitHub für jeden Workflow-Lauf erstellt
- Keine manuelle Erstellung oder Speicherung erforderlich
- Hat standardmäßig Zugriff auf das Repository, in dem der Workflow läuft
- Läuft nach dem Workflow-Lauf automatisch ab

## Einmalige Konfiguration (falls erforderlich)

In **sehr seltenen Fällen** könnte es sein, dass Workflow-Berechtigungen im Repository eingeschränkt sind. So prüfen und aktivieren Sie sie:

### 1. Repository-Einstellungen prüfen

1. Gehen Sie zu Ihrem GitHub Repository
2. Klicken Sie auf **Settings** (Einstellungen)
3. Im linken Menü: **Actions** → **General**
4. Scrollen Sie zu **Workflow permissions**

### 2. Korrekte Einstellung

Wählen Sie eine dieser Optionen:

**Option A (Empfohlen):**
- ✅ "Read and write permissions"

**Option B (Restriktiver):**
- ✅ "Read repository contents and packages permissions"
- ✅ Häkchen bei "Allow GitHub Actions to create and approve pull requests" (optional)

### 3. Speichern

Klicken Sie auf **Save** am Ende der Seite.

## So verwenden Sie den Workflow

### Via GitHub Web-Interface

1. Gehen Sie zu Ihrem Repository auf github.com
2. Klicken Sie auf den Tab **Actions**
3. In der linken Sidebar: Wählen Sie **Save System Prompt**
4. Klicken Sie rechts auf **Run workflow**
5. Füllen Sie das Formular aus:
   - **prompt_name**: "Mein neuer Prompt"
   - **prompt_description**: "Beschreibung..."
   - **prompt_content**: Der vollständige Prompt-Text
   - **created_by**: Ihr Name
6. Klicken Sie auf **Run workflow**

### Was passiert dann?

Der Workflow wird:
1. Das Repository auschecken
2. Python einrichten
3. Die `saved_prompts.json` Datei aktualisieren
4. Die Änderungen committen
5. Zum Repository pushen

Nach wenigen Sekunden sehen Sie den neuen Prompt in der App!

## Troubleshooting

### Problem: "Permission denied" Fehler

**Lösung**: Prüfen Sie die Workflow-Berechtigungen (siehe oben)

### Problem: Workflow läuft nicht

**Mögliche Ursachen:**
1. **Branch-Schutz**: Der Branch `unibe-version` könnte geschützt sein
   - Lösung: Erlauben Sie GitHub Actions im Branch-Schutz
   - Settings → Branches → Branch protection rules

2. **Actions deaktiviert**: Actions könnten für das Repository deaktiviert sein
   - Lösung: Settings → Actions → General → "Allow all actions"

### Problem: Commit wird erstellt, aber nicht gepusht

**Lösung**: Stellen Sie sicher, dass der Workflow `contents: write` Permission hat

## Alternative: Lokales Speichern + Git

Wenn Sie GitHub Actions nicht verwenden möchten, können Sie einfach lokal speichern:

1. In der App: Prompt bearbeiten
2. Auf "💾 Lokal speichern" klicken
3. Terminal/Git Bash öffnen:

```bash
cd C:\Users\Phili\Documents\Programmieren\BELEX
git add saved_prompts.json
git commit -m "Add new prompt: [Ihr Prompt-Name]"
git push origin unibe-version
```

## Sicherheitshinweise

✅ **Sicher:**
- Das `GITHUB_TOKEN` hat nur Zugriff auf das aktuelle Repository
- Token läuft automatisch ab
- Keine langlebigen Credentials erforderlich

❌ **Vermeiden:**
- Niemals persönliche Access Tokens in Workflows verwenden (außer absolut notwendig)
- Keine sensiblen Daten in Prompts speichern
- Keine API-Keys oder Passwörter in Prompt-Beschreibungen

## Weitere Informationen

- [GitHub Actions Dokumentation](https://docs.github.com/en/actions)
- [Workflow-Berechtigungen](https://docs.github.com/en/actions/security-guides/automatic-token-authentication#permissions-for-the-github_token)
