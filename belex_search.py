#!/usr/bin/env python3
"""
BELEX Search Engine - Simple query interface for the filestore
"""

import json
import sys
from pathlib import Path

from google import genai
from google.genai import types


class BELEXSearchEngine:
    def __init__(self, api_key: str, filestore_id: str):
        """Initialize the search engine with API credentials"""
        self.client = genai.Client(api_key=api_key)
        self.filestore_id = filestore_id

    def search(self, query: str):
        """
        Search the BELEX filestore with a natural language query

        Args:
            query: The search query (natural language)
        """
        print(f"\n🔍 Searching for: '{query}'\n")
        print("=" * 80)

        try:
            # Query Gemini with File Search tool (exactly like the template)
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=query,
                config=types.GenerateContentConfig(
                    tools=[
                        types.Tool(
                            file_search=types.FileSearch(
                                file_search_store_names=[self.filestore_id]
                            )
                        )
                    ]
                )
            )

            # Display the answer
            if response.text:
                print("\n📄 Answer:")
                print("-" * 80)
                print(response.text)
                print("\n" + "=" * 80)
            else:
                print("\n⚠️  No answer generated")

            # Display sources (grounding chunks)
            if hasattr(response, 'candidates') and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if hasattr(candidate, 'grounding_metadata'):
                    grounding = candidate.grounding_metadata
                    if hasattr(grounding, 'grounding_chunks') and len(grounding.grounding_chunks) > 0:
                        print("\n📚 Sources:")
                        print("-" * 80)

                        # Collect unique sources with their text snippets
                        sources_dict = {}
                        for chunk in grounding.grounding_chunks:
                            if hasattr(chunk, 'retrieved_context'):
                                context = chunk.retrieved_context
                                if hasattr(context, 'title'):
                                    title = context.title
                                    # Add text snippet if available
                                    if hasattr(context, 'text') and context.text:
                                        if title not in sources_dict:
                                            sources_dict[title] = []
                                        # Add full text snippet
                                        snippet = context.text.strip()
                                        sources_dict[title].append(snippet)
                                    elif title not in sources_dict:
                                        sources_dict[title] = []

                        # Display sources
                        for i, (title, snippets) in enumerate(sorted(sources_dict.items()), 1):
                            # Extract BSG number from title (format: "BSG xxx.xxx" or similar)
                            # Title might be like "BSG 432.311" or "BSG_432_311.pdf"
                            import re

                            # Try to extract BSG number (pattern: digits.digits or digits.digits.digits or digits.digits-digits)
                            bsg_match = re.search(r'BSG[\s_]?([\d.]+(?:-\d+)?)', title)

                            if bsg_match:
                                bsg_nr = bsg_match.group(1)
                                url = f"https://www.belex.sites.be.ch/api/de/texts_of_law/{bsg_nr}"
                                print(f"\n{i}. {title}")
                                print(f"   URL: {url}")
                            else:
                                print(f"\n{i}. {title}")

                            if snippets:
                                # Show first snippet as preview
                                print(f"   \"{snippets[0]}\"")

                        print("\n" + "=" * 80)

            return response

        except Exception as e:
            print(f"\n❌ Search failed: {e}")
            return None


def main():
    # Load configuration
    config_file = Path("config.json")
    if not config_file.exists():
        print("❌ Error: config.json not found")
        sys.exit(1)

    with open(config_file) as f:
        config = json.load(f)

    # Validate configuration
    api_key = config.get("gemini", {}).get("api_key")
    filestore_id = config.get("gemini", {}).get("filestore_id")

    if not api_key:
        print("❌ Error: gemini.api_key not found in config.json")
        sys.exit(1)

    if not filestore_id:
        print("❌ Error: gemini.filestore_id not found in config.json")
        sys.exit(1)

    # Initialize search engine
    search_engine = BELEXSearchEngine(api_key=api_key, filestore_id=filestore_id)

    # Check if query provided as command line argument
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        search_engine.search(query)
    else:
        # Interactive mode
        print("=" * 80)
        print("BELEX Search Engine - Interactive Mode")
        print("=" * 80)
        print("\nType your search queries (or 'quit' to exit)\n")

        while True:
            try:
                query = input("🔍 Search: ").strip()

                if not query:
                    continue

                if query.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye!")
                    break

                search_engine.search(query)
                print("\n")

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except EOFError:
                break


if __name__ == "__main__":
    main()
