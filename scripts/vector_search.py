#!/usr/bin/env python3
"""
Vector similarity search for book recommendations.
Takes user criteria JSON and returns top-k most similar books using
cosine similarity on pre-computed embeddings.
"""

import json
import sys
import numpy as np
from sentence_transformers import SentenceTransformer
from pathlib import Path


def cosine_similarity(a, b):
    """Calculate cosine similarity between two vectors."""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def filter_books(books, criteria):
    """Apply programmatic filters (genre, maturity, language, books_read)."""
    filtered = books

    # Filter 1: Primary genre
    if 'primary_genre' in criteria and criteria['primary_genre']:
        filtered = [b for b in filtered if b.get('genre') == criteria['primary_genre']]

    # Filter 2: Maturity level (>=)
    if 'maturity_level' in criteria and criteria['maturity_level']:
        min_maturity = criteria['maturity_level']
        filtered = [b for b in filtered if b.get('maturity_level', 3) >= min_maturity]

    # Filter 3: Language preference
    if 'language_preference' in criteria and criteria['language_preference'] != 'any':
        lang = criteria['language_preference']
        filtered = [
            b for b in filtered
            if b.get('language', 'en') == lang
            or b.get('language') == 'both'
            or b.get('language') == 'any'
        ]

    # Filter 4: Exclude already read books
    if 'books_read' in criteria and criteria['books_read']:
        read_titles_lower = [title.lower() for title in criteria['books_read']]
        filtered = [b for b in filtered if b['title'].lower() not in read_titles_lower]

    return filtered


def build_query_text(criteria):
    """Build search query from user criteria."""
    query_parts = []

    # Add tropes
    if 'tropes' in criteria and criteria['tropes']:
        query_parts.extend(criteria['tropes'])

    # Add mood preferences
    if 'mood' in criteria:
        mood = criteria['mood']
        if isinstance(mood, list):
            query_parts.extend(mood)
        elif isinstance(mood, str) and mood != 'any':
            query_parts.append(mood)

    # Add pacing
    if 'pacing' in criteria and criteria['pacing'] and criteria['pacing'] != 'any':
        query_parts.append(criteria['pacing'])

    # Add themes liked
    if 'themes_liked' in criteria and criteria['themes_liked']:
        query_parts.extend(criteria['themes_liked'])

    # Fallback: if no query parts, use genre
    if not query_parts and 'primary_genre' in criteria:
        query_parts.append(criteria['primary_genre'])

    return ' '.join(query_parts)


def vector_search(filtered_books, query_text, model, top_k=10):
    """Perform vector similarity search."""
    if not filtered_books:
        return []

    # Generate query embedding
    query_embedding = model.encode(query_text)

    # Calculate similarity for each book
    for book in filtered_books:
        if 'embedding' not in book or not book['embedding']:
            print(f"⚠️  Warning: {book['title']} has no embedding, skipping", file=sys.stderr)
            book['similarity'] = 0.0
        else:
            book['similarity'] = float(cosine_similarity(query_embedding, book['embedding']))

    # Sort by similarity and return top_k
    sorted_books = sorted(filtered_books, key=lambda b: b.get('similarity', 0), reverse=True)
    return sorted_books[:top_k]


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/vector_search.py <criteria_json_file>", file=sys.stderr)
        print("\nExample criteria JSON:", file=sys.stderr)
        print(json.dumps({
            "primary_genre": "sci-fi",
            "maturity_level": 4,
            "tropes": ["dystopian-society", "cyberpunk"],
            "mood": ["dark", "tense"],
            "pacing": "fast",
            "language_preference": "any",
            "books_read": []
        }, indent=2), file=sys.stderr)
        sys.exit(1)

    # Load criteria
    criteria_path = Path(sys.argv[1])
    with open(criteria_path, 'r', encoding='utf-8') as f:
        criteria = json.load(f)

    # Determine project root
    if criteria_path.is_absolute():
        # Criteria file might be temporary, find project root from script location
        project_root = Path(__file__).parent.parent
    else:
        project_root = Path.cwd()

    # Load catalog with embeddings
    catalog_path = project_root / 'data' / 'catalog_with_embeddings.json'

    if not catalog_path.exists():
        print(f"❌ Error: Catalog with embeddings not found at {catalog_path}", file=sys.stderr)
        print("   Run: python scripts/generate_embeddings.py first", file=sys.stderr)
        sys.exit(1)

    with open(catalog_path, 'r', encoding='utf-8') as f:
        catalog = json.load(f)

    # Handle both formats
    if isinstance(catalog, list):
        books = catalog
    elif isinstance(catalog, dict) and 'books' in catalog:
        books = catalog['books']
    else:
        print("❌ Error: Catalog format not recognized", file=sys.stderr)
        sys.exit(1)

    # Load sentence-transformers model
    print("🔧 Loading model...", file=sys.stderr)
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # 1. Apply programmatic filters
    filtered = filter_books(books, criteria)
    print(f"📊 Filtered to {len(filtered)} candidates (from {len(books)} total)", file=sys.stderr)

    if not filtered:
        print("⚠️  No books match the criteria", file=sys.stderr)
        print(json.dumps([]))
        sys.exit(0)

    # 2. Build query text
    query_text = build_query_text(criteria)
    print(f"🔍 Query: \"{query_text}\"", file=sys.stderr)

    # 3. Vector similarity search
    top_candidates = vector_search(filtered, query_text, model, top_k=10)

    # 4. Output JSON to stdout
    print(json.dumps(top_candidates, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
