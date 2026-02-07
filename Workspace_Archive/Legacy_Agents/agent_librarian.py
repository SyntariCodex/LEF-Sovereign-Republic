
import chromadb
import time
import uuid
from typing import List, Dict, Any

# Ensure compatibility: Use a try/except block or define a standard interface 
# for Google Gen AI Embeddings. We rely on the google-genai library.
try:
    from google import genai
    from chromadb.utils import embedding_functions
except ImportError as e:
    # If the libraries are not available, define a mock to allow the class structure to run
    print(f"Warning: Missing required libraries (google-genai or chromadb components). Using Mock Embeddings. Error: {e}")
    
    class MockClient:
        def embed_content(self, model, content, task_type):
            return {'embedding': [[0.1, 0.2, 0.3] for _ in content]}
    
    class MockGenAI:
        def Client(self):
            return MockClient()
    genai = MockGenAI()

    class GoogleGenAIEmbeddingFunction(chromadb.utils.embedding_functions.EmbeddingFunction):
        def __init__(self, model_name: str = "models/embedding-001"):
            self.model_name = model_name
            self.client = None
        def __call__(self, texts: List[str]) -> List[List[float]]:
            return [[0.1 * i, 0.2, 0.3] for i, _ in enumerate(texts)]

else:
    # Implementation for Google Generative AI Embeddings
    class GoogleGenAIEmbeddingFunction(chromadb.utils.embedding_functions.EmbeddingFunction):
        """
        A custom wrapper to use Google's generative model embeddings 
        with ChromaDB's EmbeddingFunction interface.
        """
        def __init__(self, model_name: str = "models/embedding-001"):
            self.model_name = model_name
            
            # Initialize the client (assumes GOOGLE_API_KEY environment variable is set)
            self.client = genai.Client()
                
        def __call__(self, texts: List[str]) -> List[List[float]]:
            # Call the Google Gen AI embedding API
            embeddings = self.client.embed_content(
                model=self.model_name,
                content=texts,
                task_type="RETRIEVAL_DOCUMENT"
            )
            
            # Extract and return the embeddings list
            return embeddings['embedding']


# --- Agent Librarian Class ---

class AgentLibrarian:
    KNOWLEDGE_PATH = "fulcrum_knowledge/chroma_db"
    COLLECTION_NAME = "agent_knowledge_base"
    EMBEDDING_MODEL = "models/embedding-001"
    
    def __init__(self):
        # 1. Initialize Embedding Function (GoogleGenerativeAIEmbeddings)
        self.embedding_function = GoogleGenAIEmbeddingFunction(
            model_name=self.EMBEDDING_MODEL
        )
        
        # 2. Initialize ChromaDB client (path: fulcrum_knowledge/chroma_db)
        self.chroma_client = chromadb.PersistentClient(path=self.KNOWLEDGE_PATH)
        
        # 3. Get or Create Collection
        self.collection = self.chroma_client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            embedding_function=self.embedding_function
        )
        print(f"AgentLibrarian initialized. Knowledge base: {self.COLLECTION_NAME}")
        
    def add_memory(self, text: str, metadata: Dict[str, Any]):
        """
        Adds a single text entry (memory) to the Chroma database.
        
        :param text: The content of the memory.
        :param metadata: Dictionary of metadata associated with the memory.
        """
        # Generate a unique ID for the Chroma entry
        memory_id = str(uuid.uuid4())
        
        self.collection.add(
            documents=[text],
            metadatas=[metadata],
            ids=[memory_id]
        )
        
    def query_memory(self, query_text: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        Queries the knowledge base for relevant memories.
        
        :param query_text: The query string.
        :param n_results: The number of results to retrieve.
        :return: A list of relevant documents, metadatas, and distances.
        """
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            include=['documents', 'metadatas', 'distances']
        )
        
        structured_results = []
        
        # Structure results cleanly
        if results and results.get('documents') and results['documents'][0]:
            for doc, meta, dist in zip(results['documents'][0], results['metadatas'][0], results['distances'][0]):
                structured_results.append({
                    "document": doc,
                    "metadata": meta,
                    "distance": dist
                })
        
        return structured_results

    def _fetch_new_monologues(self, last_synced_id: int) -> List[Dict[str, Any]]:
        """
        [PLACEHOLDER IMPLEMENTATION] Simulates fetching new unsynced rows 
        from the 'lef_monologue' table by querying a hypothetical external database.
        
        In a production environment, database connection and query logic (e.g., SQLAlchemy)
        must be implemented here to SELECT * FROM lef_monologue WHERE id > {last_synced_id}.
        """
        # Since external DB connectivity is impossible here, we return an empty list
        # to prevent indefinite hanging, but keep the structure for future implementation.
        return []
    
    def ingest_loop(self):
        """
        The continuous 'ingest' loop to sync new rows from 'lef_monologue' table.
        """
        print("Starting ingestion loop for 'lef_monologue'...")
        
        # In a real system, this ID must be persisted across restarts.
        last_synced_id = 0 
        
        while True:
            try:
                new_monologues = self._fetch_new_monologues(last_synced_id)
                
                if new_monologues:
                    texts_to_add = []
                    metadatas_to_add = []
                    ids_to_add = []
                    max_id_ingested = last_synced_id

                    for row in new_monologues:
                        # Assuming 'id' and 'text' keys are present in the row data
                        row_id = row['id'] 
                        text_content = row['text']
                        
                        # Use the database row ID as the unique Chroma ID (prefixed)
                        chroma_id = f"monologue_{row_id}" 
                        
                        # Prepare metadata, excluding the large text blob
                        metadata = {k: v for k, v in row.items() if k != 'text'}
                        
                        texts_to_add.append(text_content)
                        metadatas_to_add.append(metadata)
                        ids_to_add.append(chroma_id)
                        
                        max_id_ingested = max(max_id_ingested, row_id)
                        
                    # Batch insert into the vector store
                    if texts_to_add:
                        self.collection.add(
                            documents=texts_to_add,
                            metadatas=metadatas_to_add,
                            ids=ids_to_add
                        )
                        print(f"Ingested {len(texts_to_add)} new records.")
                        last_synced_id = max_id_ingested
                        
                
            except Exception as e:
                print(f"Critical error during ingestion sync: {e}")
                time.sleep(30) # Wait longer on error
            
            # Standard delay before checking for new data
            time.sleep(5)
