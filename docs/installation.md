# Installation & Setup Guide

## Prerequisites

This project requires **Python 3.8+** for vector search functionality.

### Install Python (Windows)

1. **Download Python**: https://www.python.org/downloads/
   - Recommended: Python 3.11 or later
   - During installation, **CHECK "Add Python to PATH"**

2. **Verify installation**:
   ```bash
   python --version
   # Should output: Python 3.x.x
   ```

## Install Dependencies

After Python is installed:

```bash
# Navigate to project directory
cd "C:\Users\jeroc\Proyectos AI\Test1- Agente Recomendador de Libros"

# Install required packages
pip install sentence-transformers numpy

# Or using python -m pip
python -m pip install sentence-transformers numpy
```

### Dependencies Installed

- **sentence-transformers** (~500MB): Provides pre-trained embedding models
  - Uses `all-MiniLM-L6-v2` model (90MB, 384 dimensions)
- **numpy**: Numerical computing for vector operations

## Generate Embeddings

Once dependencies are installed:

```bash
# Generate embeddings for all 30 books in catalog
python scripts/generate_embeddings.py

# Output: data/catalog_with_embeddings.json (~200KB)
# Time: ~30-60 seconds (first run downloads model)
```

## Test Vector Search

Create a test criteria file:

```bash
cat > test_criteria.json <<EOF
{
  "primary_genre": "sci-fi",
  "maturity_level": 4,
  "tropes": ["dystopian-society", "cyberpunk"],
  "mood": ["dark", "tense"],
  "pacing": "fast",
  "language_preference": "any",
  "books_read": []
}
EOF

# Run vector search
python scripts/vector_search.py test_criteria.json
```

Expected output: Top 10 sci-fi books with similarity scores

## Troubleshooting

### `pip: command not found`
- Python not in PATH. Reinstall Python with "Add to PATH" checked
- Or use: `python -m pip` instead of `pip`

### `sentence-transformers` download fails
- Large download (~500MB). Check internet connection.
- Try: `pip install --upgrade sentence-transformers`

### `ModuleNotFoundError: No module named 'sentence_transformers'`
- Run installation in correct Python environment
- Verify: `pip show sentence-transformers`

### Embeddings generation is slow
- First run downloads model (~90MB for all-MiniLM-L6-v2)
- Subsequent runs use cached model and are faster
- Expected time: 1-2 min first run, 30s thereafter

## Verification

Verify everything is set up correctly:

```bash
# 1. Check Python
python --version

# 2. Check dependencies
pip show sentence-transformers numpy

# 3. Generate embeddings
python scripts/generate_embeddings.py

# 4. Check output file exists
ls -lh data/catalog_with_embeddings.json

# 5. Test search
python scripts/vector_search.py test_criteria.json | head -20
```

All commands should complete without errors.

## Optional: Virtual Environment

For isolated dependency management:

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install sentence-transformers numpy

# Deactivate when done
deactivate
```

## Architecture Note

The vector search system operates in **3 phases**:

1. **One-time setup** (this guide):
   - Install Python + dependencies
   - Generate embeddings (re-run when catalog changes)

2. **Runtime** (zero tokens):
   - `scripts/vector_search.py` filters and ranks books
   - Uses pre-computed embeddings (no LLM calls)

3. **Presentation** (~1,200 tokens):
   - Claude reads top-10 JSON and generates personalized explanations

Total: **~1,700 tokens per recommendation** (vs 8,500 before)
