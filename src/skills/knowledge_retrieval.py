from pathlib import Path

ASSETS_DIR = Path("assets")

def retrieve_knowledge(document_name: str) -> str:
    """
    Retrieve domain knowledge, safety rules, or fleet history from the assets directory.
    
    Args:
        document_name: The name of the document to read. Options include:
                       'rules.txt', 'fleet_history.txt', 'guardrails.txt',
                       or 'knowledge/av_domain_glossary.md'.
                       
    Returns:
        The full text content of the requested document, or an error message if not found.
    """
    if not ASSETS_DIR.exists():
        return "Error: assets directory not found."
        
    # Prevent path traversal
    safe_name = document_name.replace("..", "").strip("/")
    doc_path = ASSETS_DIR / safe_name
    
    if not doc_path.exists() or not doc_path.is_file():
        return f"Error: Document '{document_name}' not found. Available documents: rules.txt, fleet_history.txt, guardrails.txt, knowledge/av_domain_glossary.md."
        
    try:
        with open(doc_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading document: {e}"
