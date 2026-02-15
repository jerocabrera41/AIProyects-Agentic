# Scripts - Vector Search System

This directory contains Python scripts for zero-token book recommendation via vector similarity search.

## Quick Start

```bash
# 1. Install dependencies (one-time)
pip install sentence-transformers numpy

# 2. Generate embeddings for catalog (one-time, or when catalog changes)
python scripts/generate_embeddings.py

# 3. Test vector search
python scripts/vector_search.py <criteria.json>
```

## Scripts

### `generate_embeddings.py`

Generates 384-dimensional vector embeddings for all books in `data/catalog.json`.

**What it does**:
- Loads sentence-transformers model (`all-MiniLM-L6-v2`)
- Combines book metadata into descriptive text
- Generates embedding vector for each book
- Outputs: `data/catalog_with_embeddings.json`

**Usage**:
```bash
python scripts/generate_embeddings.py
```

**Output**:
```
🔧 Loading sentence-transformers model (all-MiniLM-L6-v2)...
✓ Model loaded successfully

📖 Reading catalog from data/catalog.json...
✓ Found 30 books

🧮 Generating embeddings...
  [ 1/30] Dune                       by Frank Herbert
  [ 2/30] Neuromancer                by William Gibson
  ...

💾 Writing catalog with embeddings...
✓ Done! Embeddings saved to data/catalog_with_embeddings.json
  Total size: ~200KB
  Books: 30
  Embedding dimensions: 384
```

**When to run**:
- After initial setup
- Whenever `data/catalog.json` is modified (new books added, metadata updated)

---

### `vector_search.py`

Performs semantic similarity search on pre-computed embeddings.

**What it does**:
1. Loads user criteria from JSON file
2. Applies programmatic filters (genre, maturity, language)
3. Builds query embedding from tropes/mood/pacing
4. Calculates cosine similarity with filtered books
5. Returns top-10 most similar books

**Usage**:
```bash
python scripts/vector_search.py <criteria_file.json>
```

**Input format** (`criteria.json`):
```json
{
  "primary_genre": "sci-fi",
  "maturity_level": 4,
  "tropes": ["dystopian-society", "cyberpunk"],
  "mood": ["dark", "tense"],
  "pacing": "fast",
  "language_preference": "any",
  "books_read": ["Dune", "Neuromancer"]
}
```

**Output** (stdout):
```json
[
  {
    "id": "snow-crash-stephenson",
    "title": "Snow Crash",
    "author": "Neal Stephenson",
    "genre": "sci-fi",
    "similarity": 0.8734,
    ...
  },
  ...
]
```

**Performance**:
- **Token cost**: 0 (local execution)
- **Execution time**: ~1-2 seconds
- **Scalability**: O(n) where n = filtered candidates

---

## Integration with Claude Code

The vector search workflow in Claude Code:

```
1. User: "Quiero ciencia ficción oscura con hackers"
   ↓
2. Claude: Task(profile-extractor, haiku) → criteria.json
   Tokens: ~500
   ↓
3. Claude: Bash(python scripts/vector_search.py /tmp/criteria.json)
   Tokens: 0 (programmatic execution)
   ↓
4. Claude: Read top_10.json + generate 3 recommendations
   Tokens: ~1,200

Total: ~1,700 tokens (vs 8,500 with agent-based approach)
```

## Technical Details

### Embedding Model

- **Model**: `all-MiniLM-L6-v2` (Hugging Face)
- **Dimensions**: 384
- **Size**: ~90MB (cached after first download)
- **Speed**: ~100ms per embedding on CPU

### Similarity Metric

- **Metric**: Cosine similarity
- **Range**: [-1, 1] where 1 = identical, 0 = orthogonal, -1 = opposite
- **Formula**: `cos(θ) = (A · B) / (||A|| × ||B||)`

### Text Construction

Embeddings are generated from combined metadata:
```python
text = f"{title} by {author} {genre} {subgenre} {' '.join(tropes)} {' '.join(mood)} {pacing} {synopsis[:200]}"
```

This captures:
- Content (title, author, synopsis)
- Classification (genre, subgenre)
- Narrative elements (tropes, mood, pacing)

## Troubleshooting

### Error: `ModuleNotFoundError: No module named 'sentence_transformers'`
**Solution**: Install dependencies
```bash
pip install sentence-transformers numpy
```

### Error: `FileNotFoundError: data/catalog_with_embeddings.json`
**Solution**: Generate embeddings first
```bash
python scripts/generate_embeddings.py
```

### Warning: `{book} has no embedding, skipping`
**Cause**: Book in catalog doesn't have `embedding` field
**Solution**: Re-run `generate_embeddings.py`

### Slow performance on first run
**Cause**: Model is downloading (~90MB)
**Solution**: Wait for download to complete. Subsequent runs use cached model.

## Development

### Adding New Filters

Edit `filter_books()` in `vector_search.py`:

```python
def filter_books(books, criteria):
    # ... existing filters ...

    # New filter: exclude specific tags
    if 'tags_excluded' in criteria:
        filtered = [
            b for b in filtered
            if not any(tag in b.get('tags', []) for tag in criteria['tags_excluded'])
        ]

    return filtered
```

### Changing Embedding Model

Edit `generate_embeddings.py` and `vector_search.py`:

```python
# Replace 'all-MiniLM-L6-v2' with desired model
model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')  # For multilingual support
```

**Note**: Regenerate embeddings after model change.

## Performance Benchmarks

Based on 30-book catalog:

| Operation | Time | Tokens |
|-----------|------|--------|
| Generate embeddings | 30-60s (first run) | 0 |
| Generate embeddings | 10-15s (cached) | 0 |
| Vector search | 1-2s | 0 |
| Claude presentation | 5-10s | ~1,200 |
| **Total recommendation** | **6-12s** | **~1,700** |

Scaling to 1,000 books:
- Embeddings generation: ~5 min (one-time)
- Vector search: ~2-3s (still 0 tokens)
- **Same token consumption regardless of catalog size**
