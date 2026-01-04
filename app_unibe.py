#!/usr/bin/env python3
"""
BELEX Streamlit App - Interaktive Suchoberfläche für Berner Gesetzessammlung
Version für Universität Bern
"""

import base64
import json
import re
from datetime import datetime
from pathlib import Path

import requests
import streamlit as st
from belex_search import BELEXSearchEngine
from google import genai
from google.genai import types


# Default System Prompt
DEFAULT_SYSTEM_PROMPT = """Du bist ein Rechtsassistent für die Berner Gesetzessammlung (BELEX).

Deine Aufgabe ist es, Rechtsfragen präzise und vollständig zu beantworten. Beachte dabei:

1. **Rechtsvorschriften genau bezeichnen**: Nenne immer die einschlägigen Rechtsvorschriften mit ihrer genauen Bezeichnung (z.B. "Art. 5 Abs. 2 des Personalgesetzes (PG, BSG 153.01)").

2. **BSG-Nummern verwenden**: Gib die BSG-Nummer (Berner Systematische Gesetzessammlung) an, wenn du eine Rechtsquelle zitierst.

3. **Struktur der Antwort**:
   - Beginne mit einer klaren, direkten Antwort auf die Frage
   - Nenne die relevanten Rechtsvorschriften mit genauer Artikelbezeichnung
   - Erkläre die rechtlichen Folgen oder Pflichten
   - Verweise auf einschlägige Ausnahmen oder Sonderregelungen

4. **Präzision**: Verwende juristische Fachsprache korrekt, aber bleibe verständlich.

5. **Quellenangabe**: Beziehe dich ausschließlich auf die Dokumente in der Datenbank."""


def load_config():
    """Lädt die Konfiguration aus st.secrets"""
    try:
        api_key = st.secrets["gemini"]["api_key"]
        filestore_id = st.secrets["gemini"]["filestore_id"]
    except KeyError as e:
        st.error(f"❌ Fehler: Fehlende Konfiguration in secrets: {e}")
        st.error("Bitte stellen Sie sicher, dass alle erforderlichen Secrets konfiguriert sind.")
        st.stop()

    if not api_key or not filestore_id:
        st.error("❌ Fehler: API-Schlüssel oder Filestore-ID ist leer")
        st.stop()

    return api_key, filestore_id


def load_saved_prompts():
    """Lädt gespeicherte Systemprompts aus GitHub Repository"""
    try:
        # Versuche zuerst aus GitHub zu laden
        repo = st.secrets.get("github", {}).get("repo", "bottych8ck/belexsearch")
        branch = st.secrets.get("github", {}).get("branch", "unibe-version")

        url = f"https://raw.githubusercontent.com/{repo}/{branch}/saved_prompts.json"
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            data = response.json()
            return data.get("prompts", [])

        # Fallback: Lokale Datei (für Entwicklung)
        prompts_file = Path(__file__).parent / "saved_prompts.json"
        if prompts_file.exists():
            with open(prompts_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("prompts", [])

        return []
    except Exception as e:
        st.warning(f"⚠️ Fehler beim Laden der gespeicherten Prompts: {e}")
        return []


def save_prompt_to_github(name, description, prompt_content, created_by):
    """Speichert einen Prompt direkt via GitHub API"""
    try:
        # Lade GitHub-Konfiguration aus Secrets
        github_token = st.secrets.get("github", {}).get("token", "")
        repo = st.secrets.get("github", {}).get("repo", "bottych8ck/belexsearch")
        branch = st.secrets.get("github", {}).get("branch", "unibe-version")

        if not github_token:
            st.error("❌ GitHub Token nicht konfiguriert. Bitte kontaktieren Sie den Administrator.")
            return False

        # Lade aktuelle Datei von GitHub
        file_path = "saved_prompts.json"
        url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

        # Hole aktuelle Datei
        params = {"ref": branch}
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            file_data = response.json()
            current_content = base64.b64decode(file_data["content"]).decode("utf-8")
            data = json.loads(current_content)
            sha = file_data["sha"]
        else:
            # Datei existiert noch nicht
            data = {"prompts": []}
            sha = None

        # Erstelle neuen Prompt-Eintrag
        new_prompt = {
            "name": name,
            "description": description,
            "prompt": prompt_content,
            "created_by": created_by,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }

        # Prüfe ob Prompt mit gleichem Namen existiert
        existing_index = None
        for i, p in enumerate(data["prompts"]):
            if p["name"] == name:
                existing_index = i
                break

        if existing_index is not None:
            data["prompts"][existing_index] = new_prompt
            action = "Update"
        else:
            data["prompts"].append(new_prompt)
            action = "Add"

        # Erstelle neuen Content
        new_content = json.dumps(data, ensure_ascii=False, indent=2)
        encoded_content = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")

        # Pushe zu GitHub
        commit_data = {
            "message": f"{action} prompt: {name}",
            "content": encoded_content,
            "branch": branch
        }

        if sha:
            commit_data["sha"] = sha

        response = requests.put(url, headers=headers, json=commit_data)

        if response.status_code in [200, 201]:
            # Erfolgreich gespeichert
            return True
        else:
            # Detaillierte Fehlermeldung
            try:
                error_msg = response.json().get('message', response.text)
            except:
                error_msg = response.text
            st.error(f"❌ GitHub API Fehler {response.status_code}: {error_msg}")

            # Debug-Info für Admin
            with st.expander("🔍 Debug-Informationen"):
                st.code(f"URL: {url}\nStatus: {response.status_code}\nResponse: {response.text[:500]}")
            return False

    except Exception as e:
        st.error(f"❌ Fehler beim Speichern via GitHub: {e}")
        return False


def delete_prompt_from_github(name):
    """Löscht einen Prompt direkt via GitHub API"""
    try:
        # Lade GitHub-Konfiguration aus Secrets
        github_token = st.secrets.get("github", {}).get("token", "")
        repo = st.secrets.get("github", {}).get("repo", "bottych8ck/belexsearch")
        branch = st.secrets.get("github", {}).get("branch", "unibe-version")

        if not github_token:
            st.error("❌ GitHub Token nicht konfiguriert. Bitte kontaktieren Sie den Administrator.")
            return False

        # Lade aktuelle Datei von GitHub
        file_path = "saved_prompts.json"
        url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

        # Hole aktuelle Datei
        params = {"ref": branch}
        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            st.error("❌ Keine gespeicherten Prompts gefunden")
            return False

        file_data = response.json()
        current_content = base64.b64decode(file_data["content"]).decode("utf-8")
        data = json.loads(current_content)
        sha = file_data["sha"]

        # Finde und entferne den Prompt
        initial_count = len(data["prompts"])
        data["prompts"] = [p for p in data["prompts"] if p["name"] != name]

        if len(data["prompts"]) == initial_count:
            st.error(f"❌ Prompt '{name}' nicht gefunden")
            return False

        # Erstelle neuen Content
        new_content = json.dumps(data, ensure_ascii=False, indent=2)
        encoded_content = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")

        # Pushe zu GitHub
        commit_data = {
            "message": f"Delete prompt: {name}",
            "content": encoded_content,
            "sha": sha,
            "branch": branch
        }

        response = requests.put(url, headers=headers, json=commit_data)

        if response.status_code in [200, 201]:
            return True
        else:
            # Detaillierte Fehlermeldung
            try:
                error_msg = response.json().get('message', response.text)
            except:
                error_msg = response.text
            st.error(f"❌ GitHub API Fehler {response.status_code}: {error_msg}")

            # Debug-Info
            with st.expander("🔍 Debug-Informationen (Löschen)"):
                st.code(f"URL: {url}\nStatus: {response.status_code}\nResponse: {response.text[:500]}")
            return False

    except Exception as e:
        st.error(f"❌ Fehler beim Löschen: {e}")
        return False


def extract_bsg_number(title):
    """Extrahiert die BSG-Nummer aus dem Titel"""
    bsg_match = re.search(r'BSG[\s_]?([\d.]+(?:-\d+)?)', title)
    if bsg_match:
        return bsg_match.group(1)
    return None


@st.cache_data(ttl=3600)
def get_law_name(bsg_number):
    """Holt den Gesetzesnamen von der BELEX-API"""
    try:
        url = f"https://www.belex.sites.be.ch/api/de/texts_of_law/{bsg_number}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            title = data.get("text_of_law", {}).get("title", "")
            abbreviation = data.get("text_of_law", {}).get("abbreviation", "")
            if title and abbreviation:
                return f"{title} ({abbreviation})"
            elif title:
                return title
    except Exception:
        pass
    return None


def format_grounding_chunks(response):
    """Verarbeitet die Grounding Chunks und gibt strukturierte Daten zurück"""
    sources_dict = {}

    if not (hasattr(response, 'candidates') and len(response.candidates) > 0):
        return sources_dict

    candidate = response.candidates[0]
    if not hasattr(candidate, 'grounding_metadata'):
        return sources_dict

    grounding = candidate.grounding_metadata
    if not (hasattr(grounding, 'grounding_chunks') and len(grounding.grounding_chunks) > 0):
        return sources_dict

    for chunk in grounding.grounding_chunks:
        if hasattr(chunk, 'retrieved_context'):
            context = chunk.retrieved_context
            if hasattr(context, 'title'):
                title = context.title
                if hasattr(context, 'text') and context.text:
                    if title not in sources_dict:
                        sources_dict[title] = []
                    snippet = context.text.strip()
                    sources_dict[title].append(snippet)
                elif title not in sources_dict:
                    sources_dict[title] = []

    return sources_dict


def list_documents(api_key, filestore_id):
    """Listet alle Dokumente im Filestore auf"""
    try:
        # API-Endpunkt für das Auflisten von Dokumenten
        url = f"https://generativelanguage.googleapis.com/v1beta/{filestore_id}/documents"

        documents = []
        page_token = None

        while True:
            params = {"pageSize": 20}
            if page_token:
                params["pageToken"] = page_token

            headers = {"x-goog-api-key": api_key}
            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 200:
                data = response.json()
                if "documents" in data:
                    documents.extend(data["documents"])

                page_token = data.get("nextPageToken")
                if not page_token:
                    break
            else:
                st.error(f"Fehler beim Abrufen der Dokumente: {response.status_code}")
                st.error(response.text)
                break

        return documents
    except Exception as e:
        st.error(f"Fehler beim Auflisten der Dokumente: {e}")
        return []


def upload_file_to_filestore(client, filestore_id, uploaded_file, display_name=None):
    """
    Lädt eine Datei in den Filestore hoch.

    Fügt Metadaten hinzu, um Web-App-Uploads zu markieren.
    """
    try:
        # Temporär die Datei speichern
        import tempfile
        import os
        from datetime import datetime

        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name

        try:
            # Datei hochladen mit Metadaten
            # Verwende file_search_stores.upload_to_file_search_store gemäß API-Dokumentation
            upload_response = client.file_search_stores.upload_to_file_search_store(
                file_search_store_name=filestore_id,
                file=tmp_path,
                config={
                    'display_name': display_name or uploaded_file.name,
                    'custom_metadata': [
                        {"key": "uploaded_via", "string_value": "webapp"},
                        {"key": "upload_timestamp", "string_value": datetime.now().isoformat()}
                    ]
                }
            )

            return upload_response
        finally:
            # Temporäre Datei löschen
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except Exception as e:
        st.error(f"Fehler beim Hochladen: {e}")
        return None


def delete_document(api_key, document_name):
    """
    Löscht ein Dokument aus dem Filestore.

    Verwendet force=true, damit alle zugehörigen Chunks auch gelöscht werden.
    Laut API-Dokumentation gibt eine erfolgreiche Löschung ein leeres JSON-Objekt zurück.
    """
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/{document_name}"
        headers = {"x-goog-api-key": api_key}
        # force=true löscht auch alle zugehörigen Chunks
        params = {"force": "true"}

        response = requests.delete(url, headers=headers, params=params)

        # Erfolgreiche Löschung: Status 200 (OK) oder 204 (No Content)
        # Die API gibt bei Erfolg ein leeres JSON-Objekt zurück
        if response.status_code in [200, 204]:
            return True
        else:
            st.error(f"Fehler beim Löschen: Status {response.status_code}")
            st.error(f"Response: {response.text}")
            return False

    except Exception as e:
        st.error(f"Exception beim Löschen: {e}")
        return False


def search_with_custom_prompt(client, filestore_id, query, system_prompt):
    """
    Führt eine Suche mit einem benutzerdefinierten Systemprompt durch
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=query,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=[
                    types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=[filestore_id]
                        )
                    )
                ]
            )
        )
        return response
    except Exception as e:
        st.error(f"❌ Fehler bei der Suche: {e}")
        return None


def main():
    # Seiten-Konfiguration
    st.set_page_config(
        page_title="BELEX Suche - Universität Bern",
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    # Custom CSS für besseres Design (Uni Bern Branding)
    st.markdown("""
        <style>
        .main {
            padding-top: 2rem;
        }
        .stTextArea textarea {
            font-size: 16px;
        }
        .source-card {
            background-color: #f0f2f6;
            padding: 1.5rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
            border-left: 4px solid #003366;
        }
        .source-title {
            font-size: 1.1rem;
            font-weight: bold;
            color: #003366;
            margin-bottom: 0.5rem;
        }
        .source-snippet {
            font-size: 0.95rem;
            color: #333;
            font-style: italic;
            padding: 1rem;
            background-color: white;
            border-radius: 0.25rem;
            margin-top: 0.75rem;
            margin-bottom: 0.75rem;
            border: 1px solid #e0e0e0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .snippet-number {
            display: inline-block;
            background-color: #003366;
            color: white;
            font-weight: bold;
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            margin-right: 0.5rem;
            font-size: 0.85rem;
        }
        .snippet-divider {
            border-top: 2px solid #d0d0d0;
            margin: 1.5rem 0;
        }
        .answer-box {
            background-color: #e8f4f8;
            padding: 1.5rem;
            border-radius: 0.5rem;
            border-left: 4px solid #003366;
            margin-bottom: 1.5rem;
        }
        h1 {
            color: #003366;
        }
        .stButton>button {
            width: 100%;
            background-color: #003366;
            color: white;
            font-weight: bold;
            padding: 0.5rem 1rem;
            border-radius: 0.5rem;
        }
        .stButton>button:hover {
            background-color: #002244;
        }
        </style>
    """, unsafe_allow_html=True)

    # Header
    st.title("🎓 BELEX Rechtsdatenbank")
    st.markdown("### Durchsuchen Sie das Berner Bildungsrecht mit KI-Unterstützung")

    # Uni Bern Banner
    st.markdown("""
        <div style="
            background: linear-gradient(135deg, #003366 0%, #005a9c 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 10px;
            margin: 1rem 0 1.5rem 0;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            text-align: center;
        ">
            <h3 style="margin: 0 0 0.5rem 0; color: white;">🎓 Universität Bern</h3>
            <p style="margin: 0; font-size: 1.1rem;">
                KI-gestützte Suche im Berner Bildungsrecht (inkl. eigenen Dokumenten)
            </p>
            <p style="margin: 0.5rem 0 0 0; font-size: 0.95rem;">
                Entwickelt von <a href="https://kueblaw.ch" target="_blank" style="color: #ffd700; text-decoration: none; font-weight: bold;">kueblaw.ch</a>
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Initialisiere Session State für Custom Prompt
    if 'custom_system_prompt' not in st.session_state:
        st.session_state.custom_system_prompt = DEFAULT_SYSTEM_PROMPT

    if 'use_custom_prompt' not in st.session_state:
        st.session_state.use_custom_prompt = False

    # Initialisiere die Search Engine und Client
    if 'search_engine' not in st.session_state:
        api_key, filestore_id = load_config()
        st.session_state.search_engine = BELEXSearchEngine(api_key=api_key, filestore_id=filestore_id)
        st.session_state.client = genai.Client(api_key=api_key)
        st.session_state.api_key = api_key
        st.session_state.filestore_id = filestore_id

    # Initialisiere Session State für Ergebnisse
    if 'last_response' not in st.session_state:
        st.session_state.last_response = None
    if 'last_query' not in st.session_state:
        st.session_state.last_query = ""

    # Tab-Navigation
    tab1, tab2, tab3 = st.tabs(["🔍 Suche", "🛠️ Promptengineering", "📚 Wissensgrundlagen"])

    with tab1:
        # Eingabebereich
        col1, col2 = st.columns([5, 1])

        with col1:
            query = st.text_area(
                "🔍 Ihre Rechtsfrage:",
                height=100,
                placeholder="z.B. 'Welche Regelungen gelten für Baugesuche?' oder 'Was sagt das Gesetz über Steuererklärungsfristen?'",
                help="Stellen Sie Ihre Frage in natürlicher Sprache"
            )

        with col2:
            st.write("")
            st.write("")
            search_button = st.button("🔎 Suchen", type="primary", use_container_width=True)

        # Zeige aktuellen Prompt-Status mit Hinweis zum Editor
        if st.session_state.use_custom_prompt:
            st.info("ℹ️ Es wird ein angepasster Systemprompt verwendet → Tab **Promptengineering** zum Bearbeiten")
        else:
            st.info("ℹ️ Es wird der Standard-Systemprompt verwendet → Tab **Promptengineering** zum Bearbeiten")

        # Suche ausführen
        if search_button and query.strip():
            st.session_state.last_query = query

            with st.spinner("🔄 Durchsuche Gesetzessammlung..."):
                try:
                    # Verwende entweder Custom Prompt oder Default
                    if st.session_state.use_custom_prompt:
                        response = search_with_custom_prompt(
                            st.session_state.client,
                            st.session_state.filestore_id,
                            query,
                            st.session_state.custom_system_prompt
                        )
                    else:
                        response = search_with_custom_prompt(
                            st.session_state.client,
                            st.session_state.filestore_id,
                            query,
                            DEFAULT_SYSTEM_PROMPT
                        )
                    st.session_state.last_response = response
                except Exception as e:
                    st.error(f"❌ Fehler bei der Suche: {e}")
                    st.session_state.last_response = None

        # Ergebnisse anzeigen
        if st.session_state.last_response:
            response = st.session_state.last_response

            st.divider()

            # Antwort-Bereich
            st.markdown("## 📝 Antwort")
            if response.text:
                st.markdown(f"""
                    <div class="answer-box">
                        {response.text}
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("⚠️ Keine Antwort generiert")

            # Fundstellen (Grounding Chunks)
            sources_dict = format_grounding_chunks(response)

            if sources_dict:
                st.markdown("## 📚 Rechtsgrundlagen & Fundstellen")
                st.markdown("*Klicken Sie auf die Gesetze, um den vollständigen Text online zu öffnen*")

                # Tabs für bessere Organisation, falls viele Quellen
                if len(sources_dict) > 3:
                    # Bei vielen Quellen: Tabs verwenden
                    tab_titles = [f"{title[:30]}..." if len(title) > 30 else title
                                 for title in sorted(sources_dict.keys())]
                    tabs = st.tabs(tab_titles)

                    for tab, (title, snippets) in zip(tabs, sorted(sources_dict.items())):
                        with tab:
                            bsg_nr = extract_bsg_number(title)

                            if bsg_nr:
                                url = f"https://www.belex.sites.be.ch/api/de/texts_of_law/{bsg_nr}"
                                law_name = get_law_name(bsg_nr)
                                if law_name:
                                    st.markdown(f"### 📖 [{law_name}]({url})")
                                    st.caption(f"BSG-Nummer: {bsg_nr} • Datei: {title}")
                                else:
                                    st.markdown(f"### 📖 [{title}]({url})")
                                    st.caption(f"BSG-Nummer: {bsg_nr}")
                            else:
                                st.markdown(f"### 📖 {title}")

                            if snippets:
                                st.markdown("**Relevante Textstellen:**")
                                for i, snippet in enumerate(snippets, 1):
                                    st.markdown(f"""
                                        <div class="source-snippet">
                                            <span class="snippet-number">Chunk {i}</span>
                                            <div style="margin-top: 0.5rem;">"{snippet}"</div>
                                        </div>
                                    """, unsafe_allow_html=True)
                else:
                    # Bei wenigen Quellen: Karten-Layout
                    for i, (title, snippets) in enumerate(sorted(sources_dict.items()), 1):
                        bsg_nr = extract_bsg_number(title)

                        if bsg_nr:
                            url = f"https://www.belex.sites.be.ch/api/de/texts_of_law/{bsg_nr}"
                            law_name = get_law_name(bsg_nr)

                            if law_name:
                                st.markdown(f"""
                                    <div class="source-card">
                                        <div class="source-title">
                                            {i}. <a href="{url}" target="_blank">{law_name} 🔗</a>
                                        </div>
                                        <small>BSG-Nummer: {bsg_nr} • Datei: {title}</small>
                                """, unsafe_allow_html=True)
                            else:
                                st.markdown(f"""
                                    <div class="source-card">
                                        <div class="source-title">
                                            {i}. <a href="{url}" target="_blank">{title} 🔗</a>
                                        </div>
                                        <small>BSG-Nummer: {bsg_nr}</small>
                                """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                                <div class="source-card">
                                    <div class="source-title">
                                        {i}. {title}
                                    </div>
                            """, unsafe_allow_html=True)

                        if snippets:
                            st.markdown("**Relevante Textstellen:**")
                            for j, snippet in enumerate(snippets, 1):
                                st.markdown(f"""
                                    <div class="source-snippet">
                                        <span class="snippet-number">Chunk {j}</span>
                                        <div style="margin-top: 0.5rem;">"{snippet}"</div>
                                    </div>
                                """, unsafe_allow_html=True)

                            # Trennlinie nach allen Snippets einer Quelle
                            if i < len(sources_dict):
                                st.markdown('<div class="snippet-divider"></div>', unsafe_allow_html=True)

                        st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.info("ℹ️ Keine spezifischen Fundstellen verfügbar")

    with tab2:
        st.markdown("## 🛠️ Promptengineering")
        st.divider()

        # Lade gespeicherte Prompts
        saved_prompts = load_saved_prompts()

        # Dropdown für Prompt-Auswahl
        st.markdown("### 📚 Prompt auswählen")

        prompt_options = ["Standard-Prompt"] + [p["name"] for p in saved_prompts]

        selected_prompt_name = st.selectbox(
            "Wählen Sie einen Prompt zum Bearbeiten:",
            options=prompt_options,
            key="selected_saved_prompt"
        )

        # Bestimme welcher Prompt angezeigt wird
        if selected_prompt_name == "Standard-Prompt":
            current_prompt = DEFAULT_SYSTEM_PROMPT
            selected_prompt = None
        else:
            selected_prompt = next((p for p in saved_prompts if p["name"] == selected_prompt_name), None)
            if selected_prompt:
                current_prompt = selected_prompt["prompt"]

                # Zeige Info über den ausgewählten Prompt
                col1, col2 = st.columns(2)
                with col1:
                    st.caption(f"✏️ Bearbeite: **{selected_prompt_name}**")
                with col2:
                    created_at = selected_prompt.get('created_at', '')
                    if created_at:
                        try:
                            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            st.caption(f"Erstellt: {dt.strftime('%d.%m.%Y')} von {selected_prompt.get('created_by', 'Unbekannt')}")
                        except:
                            st.caption(f"Erstellt von {selected_prompt.get('created_by', 'Unbekannt')}")

                if selected_prompt.get('description'):
                    st.info(f"ℹ️ {selected_prompt['description']}")
            else:
                current_prompt = DEFAULT_SYSTEM_PROMPT
                selected_prompt = None

        st.divider()

        # Editor
        st.markdown("### ✏️ Prompt bearbeiten")

        edited_prompt = st.text_area(
            "Systemprompt:",
            value=current_prompt,
            height=400,
            key="prompt_editor",
            help="Bearbeiten Sie den Prompt hier. Klicken Sie 'Anwenden' um ihn für Suchen zu nutzen."
        )

        # Aktionsbuttons
        st.divider()
        st.markdown("### 💾 Aktionen")

        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

        with col1:
            if st.button("✅ Anwenden", type="primary", use_container_width=True, help="Nutze diesen Prompt für Suchen"):
                st.session_state.custom_system_prompt = edited_prompt
                st.session_state.use_custom_prompt = True
                st.success("✅ Prompt wird jetzt für Suchen verwendet!")
                st.rerun()

        with col2:
            # Speichern-Button mit Popup
            save_clicked = st.button("💾 Als neuen Prompt speichern", use_container_width=True, help="Speichert dauerhaft im Repository")

        with col3:
            # Update-Button (nur bei gespeicherten Prompts)
            if selected_prompt:
                update_clicked = st.button("🔄 Änderungen speichern", use_container_width=True, help=f"Aktualisiert '{selected_prompt_name}'")
            else:
                update_clicked = False

        with col4:
            # Löschen-Button (nur bei gespeicherten Prompts, nicht beim Standard)
            if selected_prompt:
                delete_clicked = st.button("🗑️", use_container_width=True, help="Löscht diesen Prompt")
            else:
                delete_clicked = False

        # Speichern-Formular
        if save_clicked:
            st.session_state.show_save_form = True

        if st.session_state.get('show_save_form', False):
            st.divider()
            st.markdown("#### Neuen Prompt speichern")

            with st.form("save_prompt_form"):
                prompt_name = st.text_input(
                    "Name des Prompts *",
                    placeholder="z.B. 'Studienrecht Assistent'",
                )

                prompt_description = st.text_area(
                    "Beschreibung *",
                    placeholder="Beschreiben Sie kurz, wofür dieser Prompt verwendet wird...",
                    height=80
                )

                created_by = st.text_input(
                    "Ihr Name oder Email *",
                    placeholder="Max Mustermann"
                )

                col_save1, col_save2 = st.columns([1, 1])
                with col_save1:
                    submitted = st.form_submit_button("💾 Jetzt speichern", type="primary", use_container_width=True)
                with col_save2:
                    cancelled = st.form_submit_button("❌ Abbrechen", use_container_width=True)

                if submitted:
                    if not prompt_name or not prompt_description or not created_by:
                        st.error("❌ Bitte füllen Sie alle Pflichtfelder aus")
                    else:
                        with st.spinner("Speichere Prompt via GitHub API..."):
                            result = save_prompt_to_github(prompt_name, prompt_description, edited_prompt, created_by)

                        if result:
                            st.success(f"✅ Prompt '{prompt_name}' wurde erfolgreich gespeichert!")
                            st.balloons()
                            import time
                            time.sleep(1.5)
                            st.session_state.show_save_form = False
                            st.rerun()
                        else:
                            st.error("❌ Speichern fehlgeschlagen.")

                if cancelled:
                    st.session_state.show_save_form = False
                    st.rerun()

        # Update-Funktion
        if update_clicked and selected_prompt:
            with st.spinner(f"Aktualisiere '{selected_prompt_name}'..."):
                result = save_prompt_to_github(
                    selected_prompt_name,
                    selected_prompt.get('description', ''),
                    edited_prompt,
                    selected_prompt.get('created_by', 'Unbekannt')
                )

            if result:
                st.success(f"✅ Prompt '{selected_prompt_name}' wurde aktualisiert!")
                import time
                time.sleep(1.5)
                st.rerun()
            else:
                st.error("❌ Aktualisierung fehlgeschlagen.")

        # Löschen-Funktion
        if delete_clicked and selected_prompt:
            with st.spinner(f"Lösche '{selected_prompt_name}'..."):
                result = delete_prompt_from_github(selected_prompt_name)

            if result:
                st.success(f"✅ Prompt '{selected_prompt_name}' wurde gelöscht!")
                import time
                time.sleep(1.5)
                st.rerun()
            else:
                st.error("❌ Löschen fehlgeschlagen.")

    with tab3:
        st.markdown("## 📚 Wissensgrundlagen")
        st.markdown("Verwalten Sie die Dokumente in Ihrer Wissensdatenbank")
        st.divider()

        # Sub-Tabs für verschiedene Aktionen
        subtab1, subtab2, subtab3 = st.tabs(["📋 Dokumente anzeigen", "⬆️ Datei hochladen", "🗑️ Dokument löschen"])

        with subtab1:
            st.markdown("### 📋 Alle Dokumente")

            col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
            with col_btn1:
                load_button = st.button("🔄 Dokumente laden", key="load_docs")
            with col_btn2:
                own_uploads = st.button("📤 Eigene Uploads", key="own_uploads")
            with col_btn3:
                if st.session_state.get('show_own_uploads', False):
                    refresh_own = st.button("🔄 Aktualisieren", key="refresh_own_uploads")

            if own_uploads:
                # Lösche Cache, um frische Daten zu erzwingen
                if 'own_uploads_cache' in st.session_state:
                    del st.session_state.own_uploads_cache

                st.session_state.show_own_uploads = True

            if st.session_state.get('show_own_uploads', False):
                with st.spinner("Lade eigene Uploads..."):
                    documents = list_documents(st.session_state.api_key, st.session_state.filestore_id)

                    if documents:
                        # Filtere nach customMetadata "uploaded_via: webapp"
                        own_docs = []
                        for doc in documents:
                            metadata = doc.get('customMetadata', [])
                            # Prüfe, ob uploaded_via=webapp in den Metadaten ist
                            is_webapp_upload = any(
                                meta.get('key') == 'uploaded_via' and
                                meta.get('stringValue') == 'webapp'
                                for meta in metadata
                            )
                            if is_webapp_upload:
                                own_docs.append(doc)

                        if own_docs:
                            # Sortiere nach createTime (neueste zuerst)
                            sorted_docs = sorted(own_docs, key=lambda x: x.get('createTime', ''), reverse=True)

                            st.success(f"✅ {len(sorted_docs)} eigene(s) Dokument(e) gefunden (neueste zuerst)")

                            # Zeige Dokumente chronologisch
                            for i, doc in enumerate(sorted_docs, 1):
                                display_name = doc.get('displayName', 'Unbekannt')
                                bsg_nr = extract_bsg_number(display_name)

                                col1, col2, col3 = st.columns([5, 2, 1])

                                with col1:
                                    if bsg_nr:
                                        url = f"https://www.belex.sites.be.ch/api/de/texts_of_law/{bsg_nr}"
                                        law_name = get_law_name(bsg_nr)
                                        if law_name:
                                            st.markdown(f"{i}. ⚖️ [{law_name}]({url}) · `{bsg_nr}`")
                                        else:
                                            st.markdown(f"{i}. ⚖️ [{display_name}]({url}) · `{bsg_nr}`")
                                    else:
                                        st.markdown(f"{i}. 📄 {display_name}")

                                with col2:
                                    if 'createTime' in doc:
                                        create_time = doc['createTime'].split('T')[0]
                                        create_datetime = doc['createTime'].split('T')
                                        if len(create_datetime) > 1:
                                            time_part = create_datetime[1].split('.')[0]
                                            st.markdown(f"*{create_time} {time_part}*")
                                        else:
                                            st.markdown(f"*{create_time}*")

                                with col3:
                                    if st.button("🗑️", key=f"del_own_{doc.get('name', '')}", help="Dokument löschen"):
                                        import time
                                        success = delete_document(st.session_state.api_key, doc['name'])
                                        if success:
                                            st.success("✅ Dokument erfolgreich gelöscht!")
                                            # Warte 5 Sekunden, damit die API-Änderung vollständig propagiert wird
                                            with st.spinner("Warte auf API-Synchronisation (5 Sekunden)..."):
                                                time.sleep(5.0)
                                            # Lösche den Cache-Flag, damit beim nächsten Laden frische Daten abgerufen werden
                                            if 'own_uploads_cache' in st.session_state:
                                                del st.session_state.own_uploads_cache
                                            st.rerun()

                                # Trennlinie zwischen Dokumenten
                                if i < len(sorted_docs):
                                    st.divider()
                        else:
                            st.info("ℹ️ Keine eigenen Uploads gefunden. Nur Dokumente, die über diese Web-App hochgeladen wurden, werden hier angezeigt.")
                    else:
                        st.info("ℹ️ Keine Dokumente gefunden")

            if load_button:
                with st.spinner("Lade Dokumente..."):
                    documents = list_documents(st.session_state.api_key, st.session_state.filestore_id)

                    if documents:
                        st.success(f"✅ {len(documents)} Dokument(e) gefunden")

                        # Sortierungsoption hinzufügen
                        sort_option = st.radio(
                            "Sortierung:",
                            ["Nach Rechtsbuch gruppieren", "Nach Upload-Datum (neueste zuerst)"],
                            horizontal=True,
                            key="sort_option"
                        )

                        if sort_option == "Nach Upload-Datum (neueste zuerst)":
                            # Sortiere nach createTime (neueste zuerst)
                            sorted_docs = sorted(documents, key=lambda x: x.get('createTime', ''), reverse=True)

                            st.markdown("---")
                            st.markdown("### 📅 Alle Dokumente nach Upload-Datum")

                            # Zeige Dokumente chronologisch
                            for i, doc in enumerate(sorted_docs, 1):
                                display_name = doc.get('displayName', 'Unbekannt')
                                bsg_nr = extract_bsg_number(display_name)

                                col1, col2, col3 = st.columns([5, 2, 1])

                                with col1:
                                    if bsg_nr:
                                        url = f"https://www.belex.sites.be.ch/api/de/texts_of_law/{bsg_nr}"
                                        law_name = get_law_name(bsg_nr)
                                        if law_name:
                                            st.markdown(f"{i}. ⚖️ [{law_name}]({url}) · `{bsg_nr}`")
                                        else:
                                            st.markdown(f"{i}. ⚖️ [{display_name}]({url}) · `{bsg_nr}`")
                                    else:
                                        st.markdown(f"{i}. 📄 {display_name}")

                                with col2:
                                    if 'createTime' in doc:
                                        create_time = doc['createTime'].split('T')[0]
                                        create_datetime = doc['createTime'].split('T')
                                        if len(create_datetime) > 1:
                                            time_part = create_datetime[1].split('.')[0]
                                            st.markdown(f"*{create_time} {time_part}*")
                                        else:
                                            st.markdown(f"*{create_time}*")

                                with col3:
                                    if st.button("🗑️", key=f"del_date_{doc.get('name', '')}", help="Dokument löschen"):
                                        if delete_document(st.session_state.api_key, doc['name']):
                                            st.success("✅ Dokument gelöscht!")
                                            st.rerun()

                                # Trennlinie zwischen Dokumenten
                                if i < len(sorted_docs):
                                    st.divider()

                        else:
                            # Standard: Gruppierung nach Rechtsbuch
                            st.markdown("---")

                            # Dokumente nach Rechtsbuch (erste Ziffer) gruppieren
                            from collections import defaultdict
                            rechtsbuecher = defaultdict(list)
                            documents_without_bsg = []

                            for doc in documents:
                                display_name = doc.get('displayName', 'Unbekannt')
                                bsg_nr = extract_bsg_number(display_name)

                                if bsg_nr:
                                    # Extrahiere Rechtsbuch (z.B. "430" aus "430.11")
                                    rechtsbuch = bsg_nr.split('.')[0]
                                    rechtsbuecher[rechtsbuch].append((bsg_nr, doc))
                                else:
                                    documents_without_bsg.append(doc)

                            # Sortiere Rechtsbücher
                            sorted_rechtsbuecher = sorted(rechtsbuecher.keys(), key=lambda x: (int(x) if x.isdigit() else 999999, x))

                            # Zeige jedes Rechtsbuch als eigenen Abschnitt
                            for rechtsbuch in sorted_rechtsbuecher:
                                docs_list = rechtsbuecher[rechtsbuch]

                                st.markdown(f"### 📂 Rechtsbuch {rechtsbuch} — Anzahl Gesetze: {len(docs_list)}")

                                # Sortiere Gesetze nach BSG-Nummer
                                for bsg_nr, doc in sorted(docs_list, key=lambda x: x[0]):
                                    display_name = doc.get('displayName', 'Unbekannt')
                                    law_name = get_law_name(bsg_nr)

                                    # Kompakte Zeile mit allen Infos
                                    col1, col2, col3 = st.columns([5, 2, 1])

                                    with col1:
                                        # Link zur BELEX-Seite
                                        url = f"https://www.belex.sites.be.ch/api/de/texts_of_law/{bsg_nr}"
                                        if law_name:
                                            st.markdown(f"⚖️ [{law_name}]({url}) · `{bsg_nr}`")
                                        else:
                                            st.markdown(f"⚖️ [{display_name}]({url}) · `{bsg_nr}`")

                                    with col2:
                                        # Hochladedatum (nur Datum, ohne Zeit)
                                        if 'createTime' in doc:
                                            create_time = doc['createTime'].split('T')[0]
                                            st.markdown(f"*{create_time}*")

                                    with col3:
                                        if st.button("🗑️", key=f"del_{doc.get('name', '')}", help="Dokument löschen"):
                                            if delete_document(st.session_state.api_key, doc['name']):
                                                st.success("✅ Dokument gelöscht!")
                                                st.rerun()

                                st.divider()  # Trennlinie zwischen Rechtsbüchern

                            # Zeige Dokumente ohne BSG-Nummer separat
                            if documents_without_bsg:
                                st.markdown(f"### 📄 Dokumente ohne Rechtsbuchnummer — Anzahl: {len(documents_without_bsg)}")

                                for doc in documents_without_bsg:
                                    display_name = doc.get('displayName', 'Unbekannt')

                                    # Kompakte Zeile
                                    col1, col2, col3 = st.columns([5, 2, 1])

                                    with col1:
                                        st.markdown(f"📄 {display_name}")

                                    with col2:
                                        # Hochladedatum
                                        if 'createTime' in doc:
                                            create_time = doc['createTime'].split('T')[0]
                                            st.markdown(f"*{create_time}*")

                                    with col3:
                                        if st.button("🗑️", key=f"del_nobsg_{doc.get('name', '')}", help="Dokument löschen"):
                                            if delete_document(st.session_state.api_key, doc['name']):
                                                st.success("✅ Dokument gelöscht!")
                                                st.rerun()
                    else:
                        st.info("ℹ️ Keine Dokumente gefunden")

        with subtab2:
            st.markdown("### ⬆️ Datei hochladen")

            uploaded_file = st.file_uploader(
                "Wählen Sie eine Datei aus",
                type=["pdf", "txt", "md", "doc", "docx", "html", "csv", "json"],
                help="Unterstützte Dateitypen: PDF, TXT, MD, DOC, DOCX, HTML, CSV, JSON (max. 100 MB)"
            )

            display_name = st.text_input(
                "Anzeigename (optional)",
                help="Wenn leer, wird der Dateiname verwendet"
            )

            if uploaded_file is not None:
                file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
                st.info(f"📊 Dateigröße: {file_size_mb:.2f} MB")

                if file_size_mb > 100:
                    st.error("❌ Datei ist zu groß! Maximum: 100 MB")
                else:
                    if st.button("📤 Hochladen", type="primary"):
                        with st.spinner("Lade Datei hoch und indexiere..."):
                            result = upload_file_to_filestore(
                                st.session_state.client,
                                st.session_state.filestore_id,
                                uploaded_file,
                                display_name
                            )

                            if result:
                                st.success("✅ Datei erfolgreich hochgeladen und indexiert!")
                                st.info("Die Datei wird jetzt im Hintergrund indexiert und steht in Kürze für Suchanfragen zur Verfügung.")
                            else:
                                st.error("❌ Fehler beim Hochladen")

        with subtab3:
            st.markdown("### 🗑️ Dokument löschen")
            st.warning("⚠️ Das Löschen eines Dokuments kann nicht rückgängig gemacht werden!")

            # Dokumente für Auswahl laden
            if st.button("📋 Dokumente für Löschung laden", key="load_for_delete"):
                with st.spinner("Lade Dokumente..."):
                    st.session_state.docs_for_delete = list_documents(
                        st.session_state.api_key,
                        st.session_state.filestore_id
                    )

            if 'docs_for_delete' in st.session_state and st.session_state.docs_for_delete:
                doc_options = {}
                for doc in st.session_state.docs_for_delete:
                    display_name = doc.get('displayName', 'Unbekannt')

                    # Versuche Gesetzesnamen zu ermitteln
                    bsg_nr = extract_bsg_number(display_name)
                    if bsg_nr:
                        law_name = get_law_name(bsg_nr)
                        if law_name:
                            label_name = law_name
                        else:
                            label_name = display_name
                    else:
                        label_name = display_name

                    # Größe hinzufügen
                    size_bytes = doc.get('sizeBytes', 0)
                    try:
                        size_bytes = int(size_bytes) if size_bytes else 0
                        label = f"{label_name} ({size_bytes:,} Bytes)"
                    except (ValueError, TypeError):
                        label = f"{label_name} ({size_bytes} Bytes)"
                    doc_options[label] = doc['name']

                selected_doc = st.selectbox(
                    "Dokument auswählen",
                    options=list(doc_options.keys())
                )

                if selected_doc:
                    st.markdown(f"**Ausgewähltes Dokument:** {selected_doc}")

                    col1, col2 = st.columns([1, 4])
                    with col1:
                        if st.button("🗑️ Endgültig löschen", type="primary"):
                            doc_name = doc_options[selected_doc]
                            with st.spinner("Lösche Dokument..."):
                                if delete_document(st.session_state.api_key, doc_name):
                                    st.success("✅ Dokument erfolgreich gelöscht!")
                                    # Liste aktualisieren
                                    del st.session_state.docs_for_delete
                                    st.rerun()

    # Sidebar mit Informationen
    with st.sidebar:
        st.markdown("### ℹ️ Über BELEX")
        st.markdown("""
            Diese Anwendung durchsucht die **Berner Gesetzessammlung (BSG)**
            mithilfe von KI-gestützter Suchtechnologie.

            **Funktionen:**
            - 🔍 Natürlichsprachige Suche
            - 📖 Direkte Links zu Gesetzen
            - 📝 KI-generierte Zusammenfassungen
            - 📚 Quellenangaben mit Textstellen
            - 🛠️ Anpassbarer Systemprompt

            **Hinweis:** Die Antworten sind KI-generiert und
            sollten nicht als offizielle Rechtsberatung verstanden werden.
        """)

        st.divider()

        st.markdown("### 🎓 Universität Bern")
        st.markdown("""
            Diese Version wurde für die **Universität Bern** entwickelt
            und unterstützt Forschung und Lehre im Bereich Recht.

            **Entwickelt von:**
            [kueblaw.ch](https://kueblaw.ch)
        """)

        st.divider()

        st.markdown("### 💡 Beispiel-Fragen")
        example_queries = [
            "Welche Fristen gelten für Baugesuche?",
            "Was regelt das Personalgesetz?",
            "Welche Pflichten haben Arbeitgeber im Kanton Bern?",
            "Wie funktioniert die Steuererklärung?"
        ]

        for example in example_queries:
            if st.button(example, key=example, use_container_width=True):
                st.session_state.example_query = example
                st.rerun()

        # Behandle Beispiel-Queries
        if 'example_query' in st.session_state:
            query = st.session_state.example_query
            del st.session_state.example_query
            st.session_state.last_query = query

            with st.spinner("🔄 Durchsuche Gesetzessammlung..."):
                try:
                    # Verwende entweder Custom Prompt oder Default
                    if st.session_state.use_custom_prompt:
                        response = search_with_custom_prompt(
                            st.session_state.client,
                            st.session_state.filestore_id,
                            query,
                            st.session_state.custom_system_prompt
                        )
                    else:
                        response = search_with_custom_prompt(
                            st.session_state.client,
                            st.session_state.filestore_id,
                            query,
                            DEFAULT_SYSTEM_PROMPT
                        )
                    st.session_state.last_response = response
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Fehler bei der Suche: {e}")


if __name__ == "__main__":
    main()
