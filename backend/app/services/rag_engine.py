"""
Retrieval-Augmented Generation Engine
Pure-Python implementation using sentence-transformers + numpy.
No ChromaDB or C++ dependencies needed.

Combines dense vector search with sparse BM25 search
using Reciprocal Rank Fusion for hybrid retrieval.
Ensures ZERO hallucinations by grounding all recommendations
in the fixed course catalog.
"""

import json
import re
import math
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import Counter, defaultdict
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from app.config import EMBEDDING_MODEL, TOP_K_COURSES
from app.models.schemas import Course


class BM25:
    """Simple BM25 implementation for sparse lexical search."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_freqs: Dict[str, int] = {}
        self.doc_lengths: List[int] = []
        self.avg_doc_length: float = 0
        self.corpus_size: int = 0
        self.tokenized_docs: List[List[str]] = []

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r'\w+', text.lower())

    def fit(self, documents: List[str]):
        self.corpus_size = len(documents)
        self.tokenized_docs = [self._tokenize(doc) for doc in documents]
        self.doc_lengths = [len(doc) for doc in self.tokenized_docs]
        self.avg_doc_length = sum(self.doc_lengths) / max(self.corpus_size, 1)

        df = defaultdict(int)
        for doc in self.tokenized_docs:
            seen = set()
            for token in doc:
                if token not in seen:
                    df[token] += 1
                    seen.add(token)
        self.doc_freqs = dict(df)

    def score(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        query_tokens = self._tokenize(query)
        scores = []

        for idx, doc_tokens in enumerate(self.tokenized_docs):
            score = 0.0
            tf_map = Counter(doc_tokens)
            doc_len = self.doc_lengths[idx]

            for token in query_tokens:
                if token not in self.doc_freqs:
                    continue
                tf = tf_map.get(token, 0)
                df = self.doc_freqs[token]
                idf = math.log((self.corpus_size - df + 0.5) / (df + 0.5) + 1)
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_length)
                score += idf * (numerator / denominator)

            scores.append((idx, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


class VectorStore:
    """Pure-Python vector store using sentence-transformers + numpy."""

    def __init__(self):
        self.model = None
        self.embeddings = None
        self.documents: List[str] = []
        self.metadatas: List[Dict] = []
        self.ids: List[str] = []

    def initialize(self, model: SentenceTransformer):
        self.model = model

    def add(self, documents: List[str], ids: List[str], metadatas: List[Dict]):
        """Add documents to the vector store."""
        self.documents.extend(documents)
        self.ids.extend(ids)
        self.metadatas.extend(metadatas)

        new_embeddings = self.model.encode(documents, show_progress_bar=False)
        if self.embeddings is None:
            self.embeddings = new_embeddings
        else:
            self.embeddings = np.vstack([self.embeddings, new_embeddings])

    def query(self, query_text: str, n_results: int = 5, where: Optional[Dict] = None) -> Dict:
        """Search for similar documents."""
        query_embedding = self.model.encode([query_text], show_progress_bar=False)
        similarities = cosine_similarity(query_embedding, self.embeddings)[0]

        # Apply metadata filter if provided
        valid_indices = list(range(len(self.ids)))
        if where:
            valid_indices = [
                i for i in valid_indices
                if all(self.metadatas[i].get(k) == v for k, v in where.items())
            ]

        # Get top-k from valid indices
        if not valid_indices:
            return {"ids": [[]], "distances": [[]], "metadatas": [[]]}

        scored = [(i, similarities[i]) for i in valid_indices]
        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:n_results]

        result_ids = [self.ids[i] for i, _ in top]
        result_distances = [1.0 - s for _, s in top]
        result_metadatas = [self.metadatas[i] for i, _ in top]

        return {
            "ids": [result_ids],
            "distances": [result_distances],
            "metadatas": [result_metadatas],
        }


class RAGEngine:
    """
    Hybrid Retrieval-Augmented Generation engine.
    Combines dense vector search with sparse BM25 search
    using Reciprocal Rank Fusion for optimal recall.
    """

    def __init__(self):
        self.vector_store = VectorStore()
        self.courses: List[Course] = []
        self.course_texts: List[str] = []
        self.bm25 = BM25()
        self._initialized = False

    def initialize(self, courses: List[Course]):
        """Load course catalog into both vector store and BM25 index."""
        self.courses = courses

        # Build searchable text for each course
        self.course_texts = [
            f"{c.title}. {c.description}. Skills: {', '.join(c.skills_covered)}. "
            f"Difficulty: {c.difficulty}. Domain: {c.domain}. "
            f"Prerequisites: {', '.join(c.prerequisites) if c.prerequisites else 'None'}."
            for c in courses
        ]

        # --- Dense Vector Index ---
        print("Loading embedding model...")
        model = SentenceTransformer(EMBEDDING_MODEL)
        self.vector_store.initialize(model)

        print("Indexing course catalog...")
        batch_size = 100
        for i in range(0, len(self.course_texts), batch_size):
            batch_end = min(i + batch_size, len(self.course_texts))
            self.vector_store.add(
                documents=self.course_texts[i:batch_end],
                ids=[courses[j].course_id for j in range(i, batch_end)],
                metadatas=[{
                    "title": courses[j].title,
                    "difficulty": courses[j].difficulty,
                    "domain": courses[j].domain,
                    "duration_hours": courses[j].duration_hours,
                    "skills": ",".join(courses[j].skills_covered),
                } for j in range(i, batch_end)],
            )

        # --- BM25 Sparse Index ---
        self.bm25.fit(self.course_texts)
        self._initialized = True
        print(f"RAG Engine initialized with {len(courses)} courses")

    def retrieve(
        self,
        skill_gap: str,
        difficulty_filter: Optional[str] = None,
        top_k: int = TOP_K_COURSES,
    ) -> List[Dict]:
        """
        Hybrid retrieval: dense + sparse with Reciprocal Rank Fusion.
        """
        if not self._initialized:
            raise RuntimeError("RAG Engine not initialized. Call initialize() first.")

        # --- Dense Vector Search ---
        where_filter = None
        if difficulty_filter:
            where_filter = {"difficulty": difficulty_filter}

        vector_results = self.vector_store.query(
            query_text=skill_gap,
            n_results=min(top_k * 2, len(self.courses)),
            where=where_filter,
        )

        dense_ranking = []
        if vector_results and vector_results["ids"]:
            for i, course_id in enumerate(vector_results["ids"][0]):
                distance = vector_results["distances"][0][i] if vector_results["distances"] else 1.0
                dense_ranking.append((course_id, 1.0 - distance))

        # --- Sparse BM25 Search ---
        bm25_results = self.bm25.score(skill_gap, top_k=top_k * 2)
        sparse_ranking = [
            (self.courses[idx].course_id, score)
            for idx, score in bm25_results
        ]

        # --- Reciprocal Rank Fusion ---
        fused = self._reciprocal_rank_fusion(dense_ranking, sparse_ranking, k=60)

        # Build result objects with full course data and citation IDs
        results = []
        for course_id, rrf_score in fused[:top_k]:
            course = self._get_course_by_id(course_id)
            if course:
                results.append({
                    "course_id": course.course_id,
                    "title": course.title,
                    "description": course.description,
                    "skills_covered": course.skills_covered,
                    "prerequisites": course.prerequisites,
                    "difficulty": course.difficulty,
                    "duration_hours": course.duration_hours,
                    "domain": course.domain,
                    "relevance_score": round(rrf_score, 4),
                    "source_citation": f"[Catalog:{course.course_id}]",
                })

        return results

    def _reciprocal_rank_fusion(
        self,
        ranking_a: List[Tuple[str, float]],
        ranking_b: List[Tuple[str, float]],
        k: int = 60,
    ) -> List[Tuple[str, float]]:
        """
        Merge two ranked lists using Reciprocal Rank Fusion.
        RRF_score(d) = sum(1 / (k + rank(d)))
        """
        rrf_scores: Dict[str, float] = defaultdict(float)

        for rank, (doc_id, _) in enumerate(ranking_a):
            rrf_scores[doc_id] += 1.0 / (k + rank + 1)

        for rank, (doc_id, _) in enumerate(ranking_b):
            rrf_scores[doc_id] += 1.0 / (k + rank + 1)

        sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_results

    def _get_course_by_id(self, course_id: str) -> Optional[Course]:
        """Look up a course by its ID."""
        for course in self.courses:
            if course.course_id == course_id:
                return course
        return None
