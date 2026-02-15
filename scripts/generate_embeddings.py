#!/usr/bin/env python3
"""
Generate vector embeddings for book catalog using sentence-transformers.
Combines book metadata (title, author, genre, tropes, mood, pacing) into
384-dimensional embeddings for semantic similarity search.
"""

from sentence_transformers import SentenceTransformer
import json
import sys
from pathlib import Path


def generate_book_embedding(book, model):
    """
    Generate a 384-dim embedding for a book.
    Combines: title, author, genre, subgenres, tropes, mood, pacing, synopsis.
    """
    text_components = [
        book['title'],
        f"by {book['author']}",
        book['genre'],
        ' '.join(book.get('subgenres', [])) if isinstance(book.get('subgenres'), list) else book.get('subgenre', ''),
        ' '.join(book.get('tropes', [])),
        ' '.join(book.get('mood', [])) if isinstance(book.get('mood'), list) else book.get('mood', ''),
        book.get('pacing', ''),
        book.get('synopsis', '')[:200]  # First 200 chars of synopsis
    ]

    # Filter out empty strings and join
    text = ' '.join(filter(None, text_components))
    return model.encode(text).tolist()


def main():
    # Determine base directory (project root)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    catalog_path = project_root / 'data' / 'catalog.json'
    output_path = project_root / 'data' / 'catalog_with_embeddings.json'

    print("🔧 Loading sentence-transformers model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print("✓ Model loaded successfully\n")

    print(f"📖 Reading catalog from {catalog_path}...")
    with open(catalog_path, 'r', encoding='utf-8') as f:
        catalog = json.load(f)

    # Handle both array format and object format
    if isinstance(catalog, list):
        books = catalog
    elif isinstance(catalog, dict) and 'books' in catalog:
        books = catalog['books']
    else:
        print("❌ Error: Catalog format not recognized")
        sys.exit(1)

    print(f"✓ Found {len(books)} books\n")

    print("🧮 Generating embeddings...")
    for i, book in enumerate(books, 1):
        print(f"  [{i:2d}/{len(books)}] {book['title']:<50} by {book['author']}")
        book['embedding'] = generate_book_embedding(book, model)

    print("\n💾 Writing catalog with embeddings...")

    # Preserve original format
    if isinstance(catalog, list):
        output_data = books
    else:
        output_data = catalog
        output_data['books'] = books

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    # Calculate size
    size_kb = output_path.stat().st_size // 1024

    print(f"✓ Done! Embeddings saved to {output_path}")
    print(f"  Total size: {size_kb}KB")
    print(f"  Books: {len(books)}")
    print(f"  Embedding dimensions: {len(books[0]['embedding'])}")


if __name__ == '__main__':
    main()
