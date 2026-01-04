# GitHub Token Setup für automatisches Prompt-Speichern

## Übersicht

Die App speichert Prompts jetzt **automatisch** via GitHub API - User müssen nur auf "Speichern" klicken!

## Einmalige Einrichtung (Administrator)

### Schritt 1: GitHub Personal Access Token erstellen

**WICHTIG**: Verwende einen **Fine-grained personal access token** (empfohlen) oder Classic Token.

#### Option A: Fine-grained Token (Empfohlen - Sicherer)

1. Gehe zu: https://github.com/settings/personal-access-tokens/new
2. **Token name**: "BELEX Prompt Manager"
3. **Expiration**: "No expiration" oder nach Bedarf
4. **Repository access**:
   - ✅ "Only select repositories"
   - Wähle: **bottych8ck/belexsearch**
5. **Permissions** → **Repository permissions**:
   - ✅ **Contents**: "Read and write" (für Datei-Änderungen)
   - ✅ **Metadata**: "Read-only" (automatisch ausgewählt)
6. Klicke **"Generate token"**
7. **WICHTIG**: Kopiere den Token sofort!

#### Option B: Classic Token (Einfacher, aber mehr Rechte)

1. Gehe zu: https://github.com/settings/tokens
2. Klicke **"Generate new token"** → **"Generate new token (classic)"**
3. **Note**: "BELEX Prompt Manager"
4. **Expiration**: "No expiration" oder nach Bedarf
5. **Scopes**:
   - ✅ **`repo`** (gesamter Haken - gibt vollen Repository-Zugriff)
6. Klicke **"Generate token"**
7. **WICHTIG**: Kopiere den Token sofort!

### Schritt 2: Token in Streamlit Secrets speichern

#### Für Streamlit Cloud:

1. Gehe zu: https://share.streamlit.io/
2. Öffne deine App
3. Klicke auf **Settings** → **Secrets**
4. Füge folgendes hinzu:

```toml
[github]
token = "ghp_deinTokenHier..."  # Ersetze mit deinem Token
repo = "bottych8ck/belexsearch"  # Dein Repository
branch = "unibe-version"  # Der Branch
```

5. Klicke auf **Save**
6. Die App wird automatisch neu gestartet

#### Für lokale Entwicklung:

Erstelle/bearbeite `.streamlit/secrets.toml`:

```toml
[gemini]
api_key = "dein_gemini_key"
filestore_id = "deine_filestore_id"

[github]
token = "ghp_deinTokenHier..."
repo = "bottych8ck/belexsearch"
branch = "unibe-version"
```

**WICHTIG**: Diese Datei ist in `.gitignore` und wird NICHT committed!

## Sicherheit

### ✅ Sichere Praktiken:

- Token wird in Streamlit Secrets gespeichert (verschlüsselt)
- Token wird niemals im Code oder in Logs angezeigt
- Token hat nur Zugriff auf das spezifizierte Repository
- Nur Administratoren können Token erstellen/ändern

### ⚠️ Wichtige Hinweise:

- **Niemals** den Token in Code committen
- **Niemals** den Token in öffentlichen Issues/PRs teilen
- Token regelmäßig rotieren (alle 6-12 Monate)
- Bei Verdacht auf Kompromittierung: Sofort widerrufen!

## Token widerrufen/erneuern

### Token widerrufen:

1. Gehe zu: https://github.com/settings/tokens
2. Finde den Token "BELEX Prompt Manager"
3. Klicke auf **Delete**

### Neuen Token erstellen:

1. Folge "Schritt 1" oben
2. Update die Streamlit Secrets mit dem neuen Token
3. App wird automatisch neu gestartet

## Troubleshooting

### Problem: "GitHub Token nicht konfiguriert"

**Ursache**: Token fehlt in Secrets

**Lösung**:
1. Prüfe Streamlit Cloud Secrets
2. Stelle sicher, dass `[github]` Sektion existiert
3. Token muss unter `token = "..."` stehen

### Problem: "GitHub API Fehler: 401"

**Ursache**: Token ist ungültig oder abgelaufen

**Lösung**:
1. Erstelle einen neuen Token
2. Update Streamlit Secrets
3. Restart App

### Problem: "GitHub API Fehler: 403" oder "Resource not accessible by personal access token"

**Ursache**: Token hat nicht die richtigen Berechtigungen oder falscher Token-Typ

**Lösung**:

**Für Fine-grained Token**:
1. Gehe zu: https://github.com/settings/personal-access-tokens
2. Klicke auf deinen Token
3. Prüfe **"Repository access"**:
   - Muss "bottych8ck/belexsearch" enthalten
4. Prüfe **"Permissions"**:
   - **Contents**: Muss "Read and write" sein (NICHT nur "Read-only")
5. Wenn falsch: Klicke "Regenerate token" und passe Permissions an

**Für Classic Token**:
1. Gehe zu: https://github.com/settings/tokens
2. Erstelle neuen Token
3. Scope **`repo`** muss VOLLSTÄNDIG ausgewählt sein (alle Unterpunkte)
4. Kopiere neuen Token und update Secrets

### Problem: "GitHub API Fehler: 404"

**Ursache**: Repository oder Branch nicht gefunden

**Lösung**:
1. Prüfe `repo` in Secrets: Muss Format `username/repo` haben
2. Prüfe `branch` in Secrets: Muss existieren

## Wie es funktioniert

### User-Perspektive:

1. User bearbeitet Prompt
2. Klickt "💾 Speichern"
3. Füllt Name, Beschreibung, Ersteller aus
4. App speichert automatisch via GitHub API
5. ✅ Fertig - Prompt ist dauerhaft gespeichert!

### Technisch:

1. App lädt aktuelle `saved_prompts.json` von GitHub
2. Fügt neuen/aktualisierten Prompt hinzu
3. Erstellt Base64-codierten Content
4. Macht PUT Request an GitHub API
5. GitHub erstellt automatisch Commit
6. Änderung ist sofort für alle sichtbar

## Alternative: Ohne Token

Falls du den Token nicht einrichten möchtest/kannst:

**Option 1**: User speichern lokal und committen manuell
- Benötigt Git-Kenntnisse
- Nicht benutzerfreundlich

**Option 2**: GitHub Actions Workflow
- User müssen Actions-Tab besuchen
- Mehrere Klicks nötig
- Weniger intuitiv

**Empfehlung**: Richte den Token ein - es dauert nur 5 Minuten und bietet die beste User Experience!

## Zugriffskontrolle

### Wer kann Prompts speichern?

**Aktuell**: Jeder User der App

**Einschränken** (optional):
- Füge Authentifizierung hinzu
- Prüfe Email-Domain (z.B. nur @unibe.ch)
- Whitelist bestimmter User

Beispiel-Code für Email-Validierung:

```python
if not created_by.endswith("@unibe.ch"):
    st.error("❌ Nur Unibe-Mitarbeiter können Prompts speichern")
    return
```

## Repository-Einstellungen

Stelle sicher, dass:
- ✅ Branch `unibe-version` existiert
- ✅ Datei `saved_prompts.json` existiert im Branch
- ✅ Branch ist nicht geschützt (oder Token hat Admin-Rechte)

## Monitoring

Alle Änderungen sind im Git-Log sichtbar:

```bash
git log saved_prompts.json
```

Jeder Commit zeigt:
- Wann wurde gespeichert
- Welcher Prompt wurde hinzugefügt/geändert
- Wer hat es initiiert (via Commit-Message)

## Support

Bei Problemen:
1. Prüfe die Streamlit Cloud Logs
2. Prüfe GitHub API Status: https://www.githubstatus.com/
3. Erstelle ein Issue im Repository
