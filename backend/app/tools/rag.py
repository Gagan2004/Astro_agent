import os
import re
import math
import logging
from typing import List, Dict, Tuple, Any, Optional

logger = logging.getLogger(__name__)

class SimpleTFIDF:
    """A clean, pure-Python TF-IDF implementation for offline vector search."""
    def __init__(self):
        self.documents: List[Dict[str, Any]] = []
        self.vocabulary: set = set()
        self.idf: Dict[str, float] = {}
        self.doc_vectors: List[Dict[str, float]] = []

    def tokenize(self, text: str) -> List[str]:
        # Lowercase, keep alphanumeric characters, split
        words = re.findall(r'\b\w+\b', text.lower())
        return words

    def fit_transform(self, documents: List[Dict[str, Any]]):
        self.documents = documents
        num_docs = len(documents)
        if num_docs == 0:
            logger.warning("RAG: Fit transform called with empty documents list.")
            return
            
        df: Dict[str, int] = {}
        
        for doc in self.documents:
            tokens = self.tokenize(doc["text"])
            unique_tokens = set(tokens)
            doc["tokens"] = tokens
            doc["tf"] = {}
            
            for token in tokens:
                doc["tf"][token] = doc["tf"].get(token, 0) + 1
                
            for token in unique_tokens:
                self.vocabulary.add(token)
                df[token] = df.get(token, 0) + 1
                
        # Compute IDF
        for word, count in df.items():
            self.idf[word] = math.log((1 + num_docs) / (1 + count)) + 1
            
        # Compute L2-normalized TF-IDF vector for each document
        for doc in self.documents:
            vector: Dict[str, float] = {}
            sq_sum = 0.0
            for word, tf_val in doc["tf"].items():
                tfidf_val = tf_val * self.idf[word]
                vector[word] = tfidf_val
                sq_sum += tfidf_val ** 2
                
            norm = math.sqrt(sq_sum) if sq_sum > 0 else 1.0
            normalized_vector = {w: v / norm for w, v in vector.items()}
            self.doc_vectors.append(normalized_vector)
            
        logger.info(f"RAG: Indexed {num_docs} document chunks with vocab size of {len(self.vocabulary)}.")

    def query(self, query_text: str, top_k: int = 3) -> List[Tuple[Dict[str, Any], float]]:
        query_tokens = self.tokenize(query_text)
        if not query_tokens:
            return []
            
        query_tf: Dict[str, int] = {}
        for token in query_tokens:
            query_tf[token] = query_tf.get(token, 0) + 1
            
        query_vector: Dict[str, float] = {}
        sq_sum = 0.0
        for word, tf_val in query_tf.items():
            if word in self.idf:
                tfidf_val = tf_val * self.idf[word]
                query_vector[word] = tfidf_val
                sq_sum += tfidf_val ** 2
                
        query_norm = math.sqrt(sq_sum)
        if query_norm == 0:
            return []
            
        # Normalize query vector
        query_vector = {w: v / query_norm for w, v in query_vector.items()}
        
        # Compute Cosine Similarity
        scores: List[Tuple[int, float]] = []
        for doc_idx, doc_vector in enumerate(self.doc_vectors):
            dot_product = 0.0
            for word, val in query_vector.items():
                if word in doc_vector:
                    dot_product += val * doc_vector[word]
            scores.append((doc_idx, dot_product))
            
        scores.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for doc_idx, score in scores[:top_k]:
            if score > 0.02:  # Relevancy threshold
                results.append((self.documents[doc_idx], score))
        return results

# Global RAG Instance
_rag_index = None

def get_rag_index() -> SimpleTFIDF:
    global _rag_index
    if _rag_index is None:
        _rag_index = SimpleTFIDF()
        
        # Determine paths
        # Relative to backend/app/tools/rag.py, backend is parent of app
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        notes_dir = os.path.join(base_dir, "astrology_notes")
        
        documents = []
        if os.path.exists(notes_dir):
            for filename in os.listdir(notes_dir):
                if filename.endswith(".md"):
                    filepath = os.path.join(notes_dir, filename)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read()
                        
                        # Split by level-2 markdown headers ( ## )
                        sections = re.split(r'\n(?=## )', content)
                        for section in sections:
                            section_text = section.strip()
                            if section_text:
                                documents.append({
                                    "text": section_text,
                                    "source": filename
                                })
                    except Exception as e:
                        logger.error(f"RAG: Error reading reference file {filename}: {str(e)}")
        else:
            logger.warning(f"RAG: Reference notes directory not found at {notes_dir}")
            
        _rag_index.fit_transform(documents)
        
    return _rag_index

def knowledge_lookup(query: str, limit: int = 3) -> str:
    """
    Looks up astrological references for the given query.
    Returns a concatenated string of the most relevant reference notes.
    """
    if not query or not isinstance(query, str):
        return "No query provided."
        
    try:
        index = get_rag_index()
        matches = index.query(query, top_k=limit)
        
        if not matches:
            return "No matching astrological notes found in reference guides."
            
        formatted_matches = []
        for idx, (doc, score) in enumerate(matches):
            formatted_matches.append(
                f"[Reference {idx + 1} from {doc['source']} (relevance: {score:.2f})]\n{doc['text']}"
            )
            
        return "\n\n---\n\n".join(formatted_matches)
    except Exception as e:
        logger.error(f"Error executing knowledge_lookup: {str(e)}")
        return f"Error executing lookup: {str(e)}"
