#!/usr/bin/env python3
"""
Vector similarity search for book recommendations.
Takes user criteria JSON and returns top-k most similar books using
cosine similarity on pre-computed embeddings.
"""

import json
import sys
import os
import io
import numpy as np
from pathlib import Path

os.environ['TRANSFORMERS_NO_ADVISORY_WARNINGS'] = '1'
os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'


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
        filtered = [b for b in filtered if b.get('maturity_level', 4) >= min_maturity]

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


def filter_books_by_genre(books, genre, criteria):
    """
    Filter books by a specific genre while applying other criteria filters.
    Similar to filter_books but allows specifying the genre instead of using primary_genre.
    """
    filtered = books

    # Filter 1: Specific genre
    filtered = [b for b in filtered if b.get('genre') == genre]

    # Filter 2: Maturity level (>=)
    if 'maturity_level' in criteria and criteria['maturity_level']:
        min_maturity = criteria['maturity_level']
        filtered = [b for b in filtered if b.get('maturity_level', 4) >= min_maturity]

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

    # Load sentence-transformers model (suppress stdout to keep JSON output clean)
    print("🔧 Loading model...", file=sys.stderr)
    _stdout = sys.stdout
    sys.stdout = io.StringIO()
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('all-MiniLM-L6-v2')
    sys.stdout = _stdout

    # 1. Apply programmatic filters for primary genre
    primary_filtered = filter_books(books, criteria)
    print(f"📊 Primary genre filtered: {len(primary_filtered)} candidates", file=sys.stderr)

    # 2. Build query text
    query_text = build_query_text(criteria)
    print(f"🔍 Query: \"{query_text}\"", file=sys.stderr)

    # 3. Vector similarity search on primary genre
    primary_results = vector_search(primary_filtered, query_text, model, top_k=10)

    # Tag primary results
    for book in primary_results:
        book['genre_pool'] = 'primary'

    # 4. Secondary genre search (if secondary_genres exist in criteria)
    secondary_results = []
    if 'secondary_genres' in criteria and criteria['secondary_genres']:
        print(f"🔍 Secondary genres: {criteria['secondary_genres']}", file=sys.stderr)

        # Collect IDs of primary results to avoid duplicates
        primary_ids = set(book['id'] for book in primary_results)

        # Search each secondary genre
        for secondary_genre in criteria['secondary_genres']:
            genre_filtered = filter_books_by_genre(books, secondary_genre, criteria)
            # Remove books already in primary results
            genre_filtered = [b for b in genre_filtered if b['id'] not in primary_ids]

            if genre_filtered:
                genre_results = vector_search(genre_filtered, query_text, model, top_k=5)
                secondary_results.extend(genre_results)

        # Sort combined secondary results by similarity and take top 5
        secondary_results.sort(key=lambda b: b.get('similarity', 0), reverse=True)
        secondary_results = secondary_results[:5]

        # Tag secondary results
        for book in secondary_results:
            book['genre_pool'] = 'secondary'

        print(f"📊 Secondary genre filtered: {len(secondary_results)} candidates", file=sys.stderr)

    # 5. Combine results (primary + secondary)
    all_results = primary_results + secondary_results
    print(f"📊 Total candidates: {len(all_results)} (primary: {len(primary_results)}, secondary: {len(secondary_results)})", file=sys.stderr)

    if not all_results:
        print("⚠️  No books match the criteria", file=sys.stderr)
        print(json.dumps([]))
        sys.exit(0)

    # 6. Strip embeddings from output (not needed downstream, saves ~70KB)
    for book in all_results:
        book.pop('embedding', None)

    # 7. Output JSON to stdout
    print(json.dumps(all_results, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
