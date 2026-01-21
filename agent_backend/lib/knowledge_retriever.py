import os
import glob
from typing import List, Dict
from shared.logger import get_logger

logger = get_logger("KnowledgeRetriever")

class KnowledgeRetriever:
    """
    Retrieves specific regulatory text from the Vault.
    Currently uses robust keyword/section matching.
    """
    
    def __init__(self, vault_path: str = ".agent/data/vault"):
        self.vault_path = vault_path
        self.knowledge_base = []
        self._load_vault()
        
    def _load_vault(self):
        """Loads and chunks text files from the vault."""
        self.knowledge_base = []
        files = glob.glob(os.path.join(self.vault_path, "*.txt"))
        
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Chunk by "SECTION" as it's the primary delimiter in laws
                    # This is a heuristic for the prototype
                    chunks = content.split("SECTION ")
                    
                    filename = os.path.basename(file_path)
                    
                    for chunk in chunks:
                        if not chunk.strip(): 
                            continue
                            
                        # Re-add "SECTION " if it was removed by split (except maybe the preamble)
                        # or if split removed it from the start of the chunk
                        chunk_text = "SECTION " + chunk if not chunk.startswith("THE PRIVATE SECURITY") else chunk
                        
                        self.knowledge_base.append({
                            "source": filename,
                            "content": chunk_text.strip()
                        })
                logger.info("vault_loaded", file=filename, chunks=len(chunks))
            except Exception as e:
                logger.error("vault_load_error", file=file_path, error=str(e))

    def retrieve(self, query: str, top_k: int = 3) -> List[str]:
        """
        Finds relevant chunks. 
        Prototype Logic: Keyword Scoring.
        """
        query_terms = [t.lower() for t in query.split() if len(t) > 3]
        if not query_terms:
            return []
            
        scored_chunks = []
        
        for doc in self.knowledge_base:
            score = 0
            content_lower = doc['content'].lower()
            
            # Boost for exact section number matches (e.g., "Section 9")
            if "section" in query.lower():
                import re
                section_nums = re.findall(r'section\s+(\d+)', query.lower())
                for num in section_nums:
                    if f"section {num}" in content_lower:
                        score += 50
            
            # Keyword matching
            for term in query_terms:
                if term in content_lower:
                    score += 1
            
            if score > 0:
                scored_chunks.append((score, f"[{doc['source']}] {doc['content']}"))
                
        # Sort by score desc
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        
        return [chunk[1] for chunk in scored_chunks[:top_k]]

# Singleton
retriever = KnowledgeRetriever()
