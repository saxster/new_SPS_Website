import chromadb
from chromadb.utils import embedding_functions
from google import genai
from google.genai import types
import os
import logging

class KnowledgeVault:
    """
    RAG Engine for SPS.
    Uses ChromaDB for storage and Google Gemini for synthesis.
    """
    def __init__(self):
        # 1. Connect to ChromaDB (Docker Service)
        # In production/docker, host is 'sps-chroma'. Locally via port forwarding, it's 'localhost'.
        self.chroma_host = os.getenv("CHROMA_HOST", "sps-chroma") 
        self.chroma_port = 8000 # Internal port of the container
        
        try:
            self.client = chromadb.HttpClient(host=self.chroma_host, port=self.chroma_port)
            self.collection = self.client.get_or_create_collection(name="sps_intel")
            logging.info("Connected to ChromaDB Vault.")
        except Exception as e:
            logging.error(f"ChromaDB Connection Failed: {e}. RAG will be offline.")
            self.collection = None

        # 2. Setup Google Gemini
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if self.api_key:
            self.llm_client = genai.Client(api_key=self.api_key)
        else:
            logging.warning("No GOOGLE_API_KEY found. Generation will fail.")

    def ingest(self, doc_id: str, title: str, text: str, meta: dict):
        """
        Store a document in the Vector DB.
        """
        if not self.collection: return
        
        logging.info(f"Ingesting into Vault: {title}")
        self.collection.add(
            documents=[text],
            metadatas=[{**meta, "title": title}],
            ids=[doc_id]
        )

    def ask(self, query: str) -> str:
        """
        Perform RAG: Retrieve context -> Prompt LLM -> Answer.
        """
        if not self.collection: return "System Offline: Knowledge Vault inaccessible."
        if not self.api_key: return "System Offline: Neural Engine (LLM) not configured."

        # 1. Retrieve Context
        results = self.collection.query(
            query_texts=[query],
            n_results=3
        )
        
        context_text = "\n\n".join(results['documents'][0])
        
        # 2. Construct Prompt
        system_prompt = """
        You are the 'SPS Commander', an AI Intelligence Officer for a physical security firm. 
        Answer the user's query based ONLY on the provided Context. 
        If the answer is not in the context, say 'No intelligence available on this specific topic.'
        Keep answers tactical, concise, and authoritative.
        """
        
        full_prompt = f"""
        Context from Intelligence Database:
        {context_text}

        User Query: {query}

        Response:
        """

        # 3. Generate Answer
        try:
            response = self.llm_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.3
                )
            )
            return response.text
        except Exception as e:
            logging.error(f"LLM Generation Error: {e}")
            return "Error processing intelligence request."

vault = KnowledgeVault()
