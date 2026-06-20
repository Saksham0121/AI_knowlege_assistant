"""
Keyword extraction utilities for the RAG Agent.

Extracts top keywords from ingested documents to be used
for efficient routing decisions (RAG vs LLM).
"""

import json
import logging
import re
from collections import Counter
from pathlib import Path
from typing import List

from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# Basic English stop words
STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can't", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have",
    "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's",
    "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll",
    "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself",
    "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not",
    "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours",
    "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll",
    "she's", "should", "shouldn't", "so", "some", "such", "than", "that", "that's",
    "the", "their", "theirs", "them", "themselves", "then", "there", "there's",
    "these", "they", "they'd", "they'll", "they're", "they've", "this", "those",
    "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we",
    "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when",
    "when's", "where", "where's", "which", "while", "who", "who's", "whom", "why",
    "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're",
    "you've", "your", "yours", "yourself", "yourselves", "will", "can", "may",
    "shall", "must", "might", "also", "well", "one", "two", "use", "used", "using",
}

def extract_keywords(documents: List[Document], top_n: int = 50) -> List[str]:
    """Extract the most frequent keywords from a list of documents.

    Args:
        documents: List of LangChain Document objects.
        top_n: Number of top keywords to return.

    Returns:
        List of lowercase keyword strings.
    """
    logger.info("Extracting keywords from %d documents...", len(documents))
    word_counts = Counter()

    for doc in documents:
        text = doc.page_content.lower()
        # Remove non-alphanumeric characters, keep words
        words = re.findall(r'\b[a-z]{3,}\b', text)
        
        # Filter stop words
        filtered_words = [w for w in words if w not in STOP_WORDS]
        word_counts.update(filtered_words)

    # Get the most common words
    top_keywords = [word for word, count in word_counts.most_common(top_n)]
    logger.info("Extracted %d keywords: %s", len(top_keywords), top_keywords[:10])
    return top_keywords

def save_keywords(keywords: List[str], index_path: str) -> None:
    """Save extracted keywords to a JSON file alongside the vector store."""
    file_path = Path(index_path) / "keywords.json"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump({"keywords": keywords}, f, indent=2)
    logger.info("Saved %d keywords to %s", len(keywords), file_path)

def load_keywords(index_path: str) -> List[str]:
    """Load extracted keywords from a JSON file."""
    file_path = Path(index_path) / "keywords.json"
    if not file_path.exists():
        logger.warning("No keywords file found at %s. Routing may be degraded.", file_path)
        return []
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("keywords", [])
    except Exception as e:
        logger.error("Failed to load keywords from %s: %s", file_path, e)
        return []
