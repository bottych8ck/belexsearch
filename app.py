#!/usr/bin/env python3
"""
BELEX Streamlit App - Interaktive Suchoberfläche für Berner Gesetzessammlung
"""

import re

import requests
import streamlit as st
from belex_search import BELEXSearchEngine
from google import genai
from google.genai import types


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
    """Lädt eine Datei in den Filestore hoch"""
    try:
        # Temporär die Datei speichern
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name

        try:
            # Datei hochladen
            upload_response = client.file_search.upload_to_file_search_store(
                file_search_store_name=filestore_id,
                file_path=tmp_path,
                mime_type=uploaded_file.type,
                display_name=display_name or uploaded_file.name
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
    """Löscht ein Dokument aus dem Filestore"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/{document_name}"
        headers = {"x-goog-api-key": api_key}
        params = {"force": "true"}

        response = requests.delete(url, headers=headers, params=params)

        if response.status_code == 200:
            return True
        else:
            st.error(f"Fehler beim Löschen: {response.status_code}")
            st.error(response.text)
            return False

    except Exception as e:
        st.error(f"Fehler beim Löschen: {e}")
        return False


def main():
    # Seiten-Konfiguration
    st.set_page_config(
        page_title="BELEX Suche",
        page_icon="⚖️",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    # Custom CSS für besseres Design
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
            border-left: 4px solid #1f77b4;
        }
        .source-title {
            font-size: 1.1rem;
            font-weight: bold;
            color: #1f77b4;
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
            background-color: #1f77b4;
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
            border-left: 4px solid #00a6a6;
            margin-bottom: 1.5rem;
        }
        h1 {
            color: #1e3a8a;
        }
        .stButton>button {
            width: 100%;
            background-color: #1f77b4;
            color: white;
            font-weight: bold;
            padding: 0.5rem 1rem;
            border-radius: 0.5rem;
        }
        .stButton>button:hover {
            background-color: #1557a0;
        }
        </style>
    """, unsafe_allow_html=True)

    # Header
    st.title("⚖️ BELEX Rechtsdatenbank")
    st.markdown("### Durchsuchen Sie das Berner Bildungsrecht mit KI-Unterstützung")

    # Testversions-Banner
    st.markdown("""
        <div style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 10px;
            margin: 1rem 0 1.5rem 0;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            text-align: center;
        ">
            <h3 style="margin: 0 0 0.5rem 0; color: white;">🧪 Testversion</h3>
            <p style="margin: 0; font-size: 1.1rem;">
                Für die <strong>Bildungsdirektion des Kantons Bern</strong>
            </p>
            <p style="margin: 0.5rem 0 0 0; font-size: 0.95rem;">
                Entwickelt von <a href="https://kueblaw.ch" target="_blank" style="color: #ffd700; text-decoration: none; font-weight: bold;">kueblaw.ch</a>
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.divider()

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
    tab1, tab2 = st.tabs(["🔍 Suche", "📁 Filestore-Verwaltung"])

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

        # Suche ausführen
        if search_button and query.strip():
            st.session_state.last_query = query

            with st.spinner("🔄 Durchsuche Gesetzessammlung..."):
                try:
                    response = st.session_state.search_engine.search(query)
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
        st.markdown("## 📁 Dokumente")
        st.markdown("Verwalten Sie die Dokumente in Ihrer Datenbank")
        st.divider()

        # Sub-Tabs für verschiedene Aktionen
        subtab1, subtab2, subtab3 = st.tabs(["📋 Dokumente anzeigen", "⬆️ Datei hochladen", "🗑️ Dokument löschen"])

        with subtab1:
            st.markdown("### 📋 Alle Dokumente")

            col_btn1, col_btn2 = st.columns([1, 1])
            with col_btn1:
                load_button = st.button("🔄 Dokumente laden", key="load_docs")
            with col_btn2:
                check_duplicates = st.button("🔍 Duplikate prüfen", key="check_dupes")

            if check_duplicates:
                with st.spinner("Prüfe auf Duplikate..."):
                    documents = list_documents(st.session_state.api_key, st.session_state.filestore_id)

                    if documents:
                        # Gruppiere nach Display-Name
                        from collections import defaultdict
                        name_groups = defaultdict(list)

                        for doc in documents:
                            display_name = doc.get('displayName', 'Unbekannt')
                            name_groups[display_name].append(doc)

                        # Finde Duplikate
                        duplicates = {name: docs for name, docs in name_groups.items() if len(docs) > 1}

                        if duplicates:
                            total_dupes = sum(len(docs) - 1 for docs in duplicates.values())
                            st.warning(f"⚠️ {total_dupes} Duplikat(e) gefunden in {len(duplicates)} Gruppe(n)!")

                            st.markdown("### Duplikate:")
                            for display_name, docs in sorted(duplicates.items()):
                                with st.expander(f"📄 {display_name} ({len(docs)}× vorhanden)", expanded=True):
                                    st.write(f"**Anzahl:** {len(docs)} Kopien")
                                    for i, doc in enumerate(docs, 1):
                                        st.markdown(f"**Kopie {i}:**")
                                        st.markdown(f"- ID: `{doc.get('name', 'N/A')}`")
                                        if 'createTime' in doc:
                                            st.markdown(f"- Hochgeladen: {doc['createTime']}")
                                        size_bytes = doc.get('sizeBytes', 0)
                                        try:
                                            size_bytes = int(size_bytes) if size_bytes else 0
                                            size_mb = size_bytes / (1024 * 1024)
                                            if size_mb >= 1:
                                                st.markdown(f"- Größe: {size_mb:.2f} MB")
                                            else:
                                                st.markdown(f"- Größe: {size_bytes:,} Bytes")
                                        except:
                                            pass
                                        st.divider()
                        else:
                            st.success("✅ Keine Duplikate gefunden!")
                    else:
                        st.info("ℹ️ Keine Dokumente gefunden")

            if load_button:
                with st.spinner("Lade Dokumente..."):
                    documents = list_documents(st.session_state.api_key, st.session_state.filestore_id)

                    if documents:
                        st.success(f"✅ {len(documents)} Dokument(e) gefunden")

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
                                    if st.button("🗑️", key=f"del_{doc.get('name', '')}", help="Dokument löschen"):
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
                                st.markdown("**Upload-Details:**")
                                st.json(str(result))
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

            **Hinweis:** Die Antworten sind KI-generiert und
            sollten nicht als offizielle Rechtsberatung verstanden werden.
        """)

        st.divider()

        st.markdown("### 🧪 Testversion")
        st.markdown("""
            Diese Testversion wurde für die **Bildungsdirektion des Kantons Bern** entwickelt.

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
                    response = st.session_state.search_engine.search(query)
                    st.session_state.last_response = response
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Fehler bei der Suche: {e}")


if __name__ == "__main__":
    main()
