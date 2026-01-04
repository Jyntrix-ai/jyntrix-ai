"""Keyword search using BM25 from rank-bm25."""

import logging
import re
from typing import Any, List

from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


class KeywordSearch:
    """Keyword-based search using BM25 algorithm.

    Uses rank-bm25 for efficient keyword matching and scoring.
    """

    def __init__(self):
        """Initialize keyword search."""
        self.stopwords = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'were', 'will', 'with', 'this', 'they', 'their',
            'what', 'when', 'where', 'which', 'while', 'who', 'whom', 'why',
            'would', 'could', 'should', 'have', 'has', 'had', 'been', 'being',
            'can', 'do', 'does', 'did', 'done', 'i', 'me', 'my', 'myself',
            'we', 'our', 'ours', 'you', 'your', 'yours', 'he', 'him', 'his',
            'she', 'her', 'hers', 'it', 'its', 'them', 'theirs',
        }

    def tokenize(self, text: str) -> List[str]:
        """Tokenize text for BM25.

        Args:
            text: Input text

        Returns:
            List of tokens
        """
        if not text:
            return []

        # Lowercase and extract words
        text = text.lower()
        words = re.findall(r'\b\w+\b', text)

        # Remove stopwords and short words
        tokens = [w for w in words if w not in self.stopwords and len(w) > 2]

        return tokens

    def search(
        self,
        query: str,
        documents: List[dict[str, Any]],
        limit: int = 10,
        content_field: str = "content",
    ) -> List[dict[str, Any]]:
        """Search documents using BM25.

        Args:
            query: Search query
            documents: List of documents with content field
            limit: Maximum results to return
            content_field: Name of the content field in documents

        Returns:
            List of results with BM25 scores
        """
        if not query or not documents:
            return []

        try:
            # Tokenize query
            query_tokens = self.tokenize(query)

            if not query_tokens:
                return []

            # Tokenize all documents
            tokenized_docs = []
            valid_doc_indices = []

            for i, doc in enumerate(documents):
                content = doc.get(content_field, "")
                # Also include keywords if present
                keywords = doc.get("keywords", [])
                full_content = f"{content} {' '.join(keywords)}"

                tokens = self.tokenize(full_content)
                if tokens:
                    tokenized_docs.append(tokens)
                    valid_doc_indices.append(i)

            if not tokenized_docs:
                return []

            # Build BM25 index
            bm25 = BM25Okapi(tokenized_docs)

            # Get scores
            scores = bm25.get_scores(query_tokens)

            # Create results with scores
            results = []
            for idx, score in enumerate(scores):
                if score > 0:
                    doc_idx = valid_doc_indices[idx]
                    doc = documents[doc_idx]

                    results.append({
                        "memory_id": doc.get("id", ""),
                        "content": doc.get(content_field, ""),
                        "memory_type": doc.get("memory_type", ""),
                        "keywords": doc.get("keywords", []),
                        "reliability": doc.get("reliability", 0.5),
                        "created_at": doc.get("created_at", ""),
                        "access_count": doc.get("access_count", 0),
                        "keyword_score": float(score),
                        "score": float(score),  # For hybrid ranking
                        "match_type": "keyword",
                    })

            # Sort by score and limit
            results.sort(key=lambda x: x["score"], reverse=True)

            return results[:limit]

        except Exception as e:
            logger.error(f"BM25 search error: {e}")
            return []

    def search_with_highlights(
        self,
        query: str,
        documents: List[dict[str, Any]],
        limit: int = 10,
        content_field: str = "content",
    ) -> List[dict[str, Any]]:
        """Search with keyword highlighting.

        Args:
            query: Search query
            documents: Documents to search
            limit: Maximum results
            content_field: Content field name

        Returns:
            Results with highlighted content
        """
        results = self.search(query, documents, limit, content_field)

        # Get query tokens for highlighting
        query_tokens = set(self.tokenize(query))

        for result in results:
            content = result.get("content", "")
            highlighted = self._highlight_matches(content, query_tokens)
            result["highlighted_content"] = highlighted

        return results

    def _highlight_matches(self, text: str, query_tokens: set) -> str:
        """Add highlighting to matched terms.

        Args:
            text: Original text
            query_tokens: Set of query tokens

        Returns:
            Text with <mark> tags around matches
        """
        if not text or not query_tokens:
            return text

        def replace_match(match):
            word = match.group(0)
            if word.lower() in query_tokens:
                return f"<mark>{word}</mark>"
            return word

        return re.sub(r'\b\w+\b', replace_match, text)

    def extract_keywords(
        self,
        text: str,
        max_keywords: int = 10,
    ) -> List[str]:
        """Extract important keywords from text.

        Uses term frequency to identify important words.

        Args:
            text: Input text
            max_keywords: Maximum keywords to extract

        Returns:
            List of keywords
        """
        tokens = self.tokenize(text)

        if not tokens:
            return []

        # Count frequencies
        freq = {}
        for token in tokens:
            freq[token] = freq.get(token, 0) + 1

        # Sort by frequency and return top keywords
        sorted_keywords = sorted(freq.items(), key=lambda x: x[1], reverse=True)

        return [k for k, _ in sorted_keywords[:max_keywords]]

    def find_matching_keywords(
        self,
        query: str,
        document_keywords: List[str],
    ) -> tuple[List[str], float]:
        """Find matching keywords between query and document.

        Args:
            query: Search query
            document_keywords: Keywords from document

        Returns:
            Tuple of (matching keywords, match ratio)
        """
        query_tokens = set(self.tokenize(query))
        doc_tokens = set(k.lower() for k in document_keywords)

        matches = query_tokens.intersection(doc_tokens)

        if not query_tokens:
            return [], 0.0

        match_ratio = len(matches) / len(query_tokens)

        return list(matches), match_ratio


class CachedKeywordSearch(KeywordSearch):
    """Keyword search with caching for repeated queries."""

    def __init__(self):
        """Initialize with cache."""
        super().__init__()
        self._bm25_cache: dict[str, BM25Okapi] = {}
        self._max_cache_size = 100

    def _get_cache_key(self, documents: List[dict]) -> str:
        """Generate cache key for document set.

        Args:
            documents: List of documents

        Returns:
            Cache key string
        """
        # Use hash of document IDs
        doc_ids = sorted([str(d.get("id", i)) for i, d in enumerate(documents)])
        return ":".join(doc_ids[:20])  # Limit key length

    def search(
        self,
        query: str,
        documents: List[dict[str, Any]],
        limit: int = 10,
        content_field: str = "content",
    ) -> List[dict[str, Any]]:
        """Cached BM25 search.

        Args:
            query: Search query
            documents: Documents to search
            limit: Maximum results
            content_field: Content field name

        Returns:
            Search results
        """
        # For small document sets, use standard search
        if len(documents) < 50:
            return super().search(query, documents, limit, content_field)

        # Try to use cached BM25 index
        cache_key = self._get_cache_key(documents)

        if cache_key not in self._bm25_cache:
            # Build and cache index
            tokenized_docs = []
            for doc in documents:
                content = doc.get(content_field, "")
                keywords = doc.get("keywords", [])
                full_content = f"{content} {' '.join(keywords)}"
                tokenized_docs.append(self.tokenize(full_content))

            if tokenized_docs:
                self._bm25_cache[cache_key] = BM25Okapi(tokenized_docs)

                # Evict old entries if cache is too large
                if len(self._bm25_cache) > self._max_cache_size:
                    oldest_key = next(iter(self._bm25_cache))
                    del self._bm25_cache[oldest_key]

        # Use cached index if available
        if cache_key in self._bm25_cache:
            query_tokens = self.tokenize(query)
            if not query_tokens:
                return []

            bm25 = self._bm25_cache[cache_key]
            scores = bm25.get_scores(query_tokens)

            results = []
            for idx, score in enumerate(scores):
                if score > 0:
                    doc = documents[idx]
                    results.append({
                        "memory_id": doc.get("id", ""),
                        "content": doc.get(content_field, ""),
                        "memory_type": doc.get("memory_type", ""),
                        "keywords": doc.get("keywords", []),
                        "reliability": doc.get("reliability", 0.5),
                        "created_at": doc.get("created_at", ""),
                        "access_count": doc.get("access_count", 0),
                        "keyword_score": float(score),
                        "score": float(score),
                        "match_type": "keyword",
                    })

            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:limit]

        return super().search(query, documents, limit, content_field)
