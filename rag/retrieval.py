"""RAG retrieval using TF-IDF for document search."""
from pathlib import Path
from typing import List, Dict, Any
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


class DocumentChunk:
    """Represents a chunk of document content."""
    
    def __init__(self, chunk_id: str, content: str, source: str, metadata: Dict[str, Any] = None):
        self.chunk_id = chunk_id
        self.content = content
        self.source = source
        self.metadata = metadata or {}
        self.score = 0.0


class TFIDFRetriever:
    """TF-IDF based document retriever."""
    
    def __init__(self, docs_dir: str, chunk_size: int = 200):
        """Initialize retriever with documents directory."""
        self.docs_dir = Path(docs_dir)
        self.chunk_size = chunk_size
        self.chunks: List[DocumentChunk] = []
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words='english',
            ngram_range=(1, 2),
            max_features=1000
        )
        self.tfidf_matrix = None
        self._load_and_chunk_documents()
    
    def _load_and_chunk_documents(self):
        """Load all markdown documents and create chunks."""
        if not self.docs_dir.exists():
            raise FileNotFoundError(f"Docs directory not found: {self.docs_dir}")
        
        for doc_path in self.docs_dir.glob("*.md"):
            content = doc_path.read_text(encoding='utf-8')
            source = doc_path.stem
            
            # Split into paragraphs and sections
            chunks = self._chunk_document(content, source)
            self.chunks.extend(chunks)
        
        # Build TF-IDF matrix
        if self.chunks:
            corpus = [chunk.content for chunk in self.chunks]
            self.tfidf_matrix = self.vectorizer.fit_transform(corpus)
    
    def _chunk_document(self, content: str, source: str) -> List[DocumentChunk]:
        """Split document into chunks."""
        chunks = []
        
        # Split by double newlines (paragraphs) or headers
        sections = re.split(r'\n\n+', content.strip())
        
        chunk_idx = 0
        for section in sections:
            section = section.strip()
            if not section:
                continue
            
            # If section is too long, split by sentences
            if len(section) > self.chunk_size * 2:
                sentences = re.split(r'[.!?]\s+', section)
                current_chunk = ""
                
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) < self.chunk_size * 2:
                        current_chunk += sentence + ". "
                    else:
                        if current_chunk:
                            chunk_id = f"{source}::chunk{chunk_idx}"
                            chunks.append(DocumentChunk(chunk_id, current_chunk.strip(), source))
                            chunk_idx += 1
                        current_chunk = sentence + ". "
                
                if current_chunk:
                    chunk_id = f"{source}::chunk{chunk_idx}"
                    chunks.append(DocumentChunk(chunk_id, current_chunk.strip(), source))
                    chunk_idx += 1
            else:
                chunk_id = f"{source}::chunk{chunk_idx}"
                chunks.append(DocumentChunk(chunk_id, section, source))
                chunk_idx += 1
        
        return chunks
    
    def retrieve(self, query: str, top_k: int = 3) -> List[DocumentChunk]:
        """Retrieve top-k most relevant chunks for a query."""
        if not self.chunks or self.tfidf_matrix is None:
            return []
        
        # Transform query
        query_vec = self.vectorizer.transform([query])
        
        # Calculate cosine similarity
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        # Create result chunks with scores
        results = []
        for idx in top_indices:
            chunk = self.chunks[idx]
            chunk.score = float(similarities[idx])
            results.append(chunk)
        
        return results
    
    def get_chunk_by_id(self, chunk_id: str) -> DocumentChunk:
        """Get a specific chunk by ID."""
        for chunk in self.chunks:
            if chunk.chunk_id == chunk_id:
                return chunk
        return None
    
    def get_all_chunks(self) -> List[DocumentChunk]:
        """Get all document chunks."""
        return self.chunks
