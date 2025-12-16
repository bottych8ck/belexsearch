# BELEX Streamlit Cloud Deployment Anleitung

## Vorbereitung

### 1. Repository vorbereiten

Die App ist jetzt so umgebaut, dass alle sensiblen Daten über `st.secrets` laufen.

**Wichtig:** Die Datei `.streamlit/secrets.toml` enthält echte API-Keys und wird NICHT in Git committed (steht in `.gitignore`).

### 2. Secrets in Streamlit Cloud konfigurieren

Wenn du die App auf Streamlit Cloud deployst, musst du die Secrets dort manuell eintragen:

1. Gehe zu deiner App in Streamlit Cloud
2. Klicke auf **Settings** (⚙️)
3. Wähle **Secrets** aus der Seitenleiste
4. Füge folgenden Inhalt ein:

```toml
[gemini]
api_key = "YOUR_GOOGLE_GEMINI_API_KEY"
filestore_id = "YOUR_FILESTORE_ID"
project_id = "YOUR_PROJECT_NAME"
```

5. Klicke auf **Save**

### 3. Requirements.txt prüfen

Stelle sicher, dass alle Abhängigkeiten in `requirements.txt` vorhanden sind:

```txt
streamlit
google-genai
requests
```

### 4. App deployen

1. Pushe den Code zu GitHub (ohne secrets.toml!)
2. In Streamlit Cloud: **New app**
3. Wähle dein Repository und Branch
4. Main file path: `app.py`
5. Konfiguriere die Secrets (siehe Schritt 2)
6. Klicke auf **Deploy**

## Lokale Entwicklung

Für lokale Entwicklung:

1. Kopiere `.streamlit/secrets.toml.example` zu `.streamlit/secrets.toml`
2. Fülle deine echten API-Keys ein
3. Starte die App mit `streamlit run app.py`

## Wichtige Änderungen

- `config.json` wird nicht mehr verwendet
- Alle sensiblen Daten sind jetzt in `st.secrets`
- API-Keys und Filestore-IDs müssen in Streamlit Cloud Secrets konfiguriert werden

## Troubleshooting

Falls die App in Streamlit Cloud nicht startet:

1. Prüfe, ob die Secrets korrekt konfiguriert sind
2. Schau dir die Logs in Streamlit Cloud an
3. Stelle sicher, dass alle Dependencies installiert sind
