# Tools Documentation

Technical documentation for the book recommendation system tools.

## Architecture Overview

```
User Input (natural language, ES or EN)
        |
        v
┌─────────────────────────────────────────────┐
│  extract_profile.py (Haiku, ~500 tokens)    │
│  ============================================ │
│  - Reads profile-extractor.md rules         │
│  - Calls Anthropic API (claude-haiku-4)     │
│  - Validates against user-profile.schema    │
│  - Writes .cache/criteria.json              │
│                                               │
│  Cost: ~$0.13/1M tokens                      │
│  Latency: ~1-2 seconds                       │
└─────────────────────────────────────────────┘
        |
        v
┌─────────────────────────────────────────────┐
│  vector_search.py (0 tokens, local Python)  │
│  ============================================ │
│  - Filters by genre/maturity/language       │
│  - Computes cosine similarity (384-dim)     │
│  - Returns top-15 (10 primary + 5 secondary)│
│  - Writes to stdout (JSON)                  │
│                                               │
│  Cost: $0 (local execution)                  │
│  Latency: ~500ms                             │
└─────────────────────────────────────────────┘
        |
        v
┌─────────────────────────────────────────────┐
│ present_recommendations.py (Sonnet, ~1200)  │
│ ============================================= │
│ - Reads recommendation-presenter.md rules   │
│ - Selects Best Match / Discovery / Secondary│
│ - Calls Anthropic API (claude-sonnet-4)     │
│ - Validates against recommendation.schema   │
│ - Outputs markdown to stdout                │
│                                               │
│ Cost: ~$3/1M tokens                          │
│ Latency: ~2-3 seconds                        │
└─────────────────────────────────────────────┘
        |
        v
User sees 3 recommendations in their language
```

## Tool 1: extract_profile.py

### Purpose
Extracts structured user reading preferences from natural language input using the Anthropic API.

### Command Line Interface

```bash
python scripts/extract_profile.py "<user_input>"
```

**Arguments:**
- `<user_input>` (positional, required): Natural language text describing reading preferences

**Example:**
```bash
python scripts/extract_profile.py "Me gusta la ciencia ficción hard y las distopías"
```

### Input Format
- **Type:** String (UTF-8 encoded)
- **Language:** Spanish or English
- **Content:** Free-form description of reading preferences, can include:
  - Genres (e.g., "ciencia ficción", "fantasy")
  - Themes (e.g., "time travel", "political intrigue")
  - Mood preferences (e.g., "dark", "adventurous")
  - Books already read (e.g., "I've read 1984")
  - Books liked/disliked

### Output Format

**Success:**
```json
{
  "status": "success",
  "file": ".cache/criteria.json",
  "tokens_used": 520
}
```

**Error:**
```json
{
  "status": "error",
  "message": "Error description here"
}
```

### Output File: `.cache/criteria.json`

Structure (conforms to `schemas/user-profile.schema.json`):
```json
{
  "primary_genre": "sci-fi",
  "secondary_genres": ["fantasy", "literary-fiction"],
  "themes_liked": ["time-travel", "dystopian-society"],
  "themes_disliked": [],
  "mood": ["dark", "tense"],
  "mood_preference": "dark",
  "complexity_preference": "challenging",
  "language_preference": "en",
  "maturity_level": 4,
  "tropes": ["dystopian-society", "political-intrigue", "cyberpunk"],
  "pacing": "moderate",
  "books_read": ["1984", "Fundación"],
  "books_liked": [],
  "books_disliked": [],
  "interaction_language": "es",
  "raw_input": "Me gusta la ciencia ficción hard y las distopías. Leí 1984 y Fundación."
}
```

### Implementation Details

**API Configuration:**
- Model: `claude-haiku-4-20250514`
- Max tokens: 2000
- Temperature: 0 (deterministic extraction)
- API key: From `ANTHROPIC_API_KEY` environment variable

**System Prompt Components:**
1. Full content of `.claude/agents/profile-extractor.md` (extraction rules)
2. JSON schema from `schemas/user-profile.schema.json`
3. Genre mapping data from `data/genre-mapping.json` (Spanish→English normalization)
4. Genre adjacency data from `data/genre-adjacency.json` (secondary genre inference)

**Response Processing:**
1. Strip markdown code fences if present (`\`\`\`json ... \`\`\``)
2. Parse JSON
3. Validate against schema using `jsonschema` library
4. Write validated JSON to `.cache/criteria.json`

**Error Handling:**
- API errors → Return error JSON with message
- JSON parsing errors → Return error JSON with parse error
- Schema validation errors → Return error JSON with validation error
- Missing API key → Return error JSON with env var message

### Token Consumption
- **Average:** ~500 tokens per request
- **Breakdown:**
  - Input tokens: ~400 (system prompt + user message)
  - Output tokens: ~100 (JSON response)

### Bilingual Support
- **Detection:** Automatically detects input language
- **Normalization:** Spanish genre names are normalized to English using `genre-mapping.json`
- **Output:** `interaction_language` field set to "es" or "en" for downstream formatting

---

## Tool 2: vector_search.py

### Purpose
Finds similar books using cosine similarity on pre-computed embeddings. Filters by genre, maturity level, language, and excludes already-read books.

### Command Line Interface

```bash
python scripts/vector_search.py <criteria_json_file>
```

**Arguments:**
- `<criteria_json_file>` (positional, required): Path to criteria JSON file (usually `.cache/criteria.json`)

**Example:**
```bash
python scripts/vector_search.py .cache/criteria.json > .cache/search_results.json
```

### Input Format

**File:** JSON file conforming to `schemas/user-profile.schema.json`

**Required fields:**
- `primary_genre`: String (sci-fi, fantasy, thriller, romance, horror, literary-fiction)
- `language_preference`: String (es, en, any)

**Optional fields:**
- `secondary_genres`: Array of genre strings
- `maturity_level`: Integer (1-5)
- `books_read`: Array of book titles to exclude
- `tropes`, `mood`, `pacing`, `themes_liked`: Used to build query text

### Output Format

**Structure:** JSON array of book objects with similarity scores

```json
[
  {
    "id": "neuromancer-william-gibson",
    "title": "Neuromancer",
    "author": "William Gibson",
    "genre": "sci-fi",
    "language": "en",
    "maturity_level": 4,
    "tropes": ["cyberpunk", "hacker", "ai-consciousness"],
    "themes": ["technology", "identity", "corporate-power"],
    "synopsis": "...",
    "similarity": 0.87,
    "genre_pool": "primary"
  },
  {
    "id": "the-left-hand-of-darkness-ursula-le-guin",
    "title": "The Left Hand of Darkness",
    "author": "Ursula K. Le Guin",
    "genre": "sci-fi",
    "similarity": 0.82,
    "genre_pool": "primary"
  },
  ...
  {
    "id": "the-name-of-the-wind-patrick-rothfuss",
    "title": "The Name of the Wind",
    "author": "Patrick Rothfuss",
    "genre": "fantasy",
    "similarity": 0.68,
    "genre_pool": "secondary"
  }
]
```

**Fields:**
- `similarity`: Float (0.0-1.0) cosine similarity score
- `genre_pool`: String ("primary" or "secondary") - indicates if book is from primary or secondary genre
- All other fields are from the catalog

**Result Count:**
- Up to 10 books from `primary_genre` pool
- Up to 5 books from `secondary_genres` pool
- Total: Up to 15 candidates

### Implementation Details

**Filtering Pipeline:**
1. **Primary Genre Search:**
   - Filter by `genre == primary_genre`
   - Filter by `maturity_level >= criteria.maturity_level`
   - Filter by `language` matching `language_preference` (or "both"/"any" books)
   - Exclude books in `books_read` (case-insensitive title match)
   - Compute similarity scores, return top-10

2. **Secondary Genre Search** (if `secondary_genres` exists):
   - For each secondary genre:
     - Filter by `genre == secondary_genre`
     - Apply same maturity, language, books_read filters
     - Exclude books already in primary results (by ID)
     - Compute similarity scores
   - Combine all secondary results, sort by similarity, take top-5

**Query Text Construction:**
Concatenates (space-separated):
1. All tropes from criteria
2. All mood values (array or string)
3. Pacing value
4. All themes_liked values
5. Fallback: primary_genre if no other query parts

**Embedding Model:**
- Model: `all-MiniLM-L6-v2` (sentence-transformers)
- Dimensionality: 384
- Similarity: Cosine similarity

**Catalog:**
- File: `data/catalog_with_embeddings.json`
- Pre-computed embeddings for all books
- Embeddings are stripped from output to reduce payload size

### Token Consumption
- **0 tokens** (local Python execution, no API calls)

### Performance
- **Latency:** ~500ms typical
- **Dependencies:** sentence-transformers, numpy

---

## Tool 3: present_recommendations.py

### Purpose
Selects 3 personalized book recommendations from search results and generates formatted markdown output using the Anthropic API.

### Command Line Interface

```bash
python scripts/present_recommendations.py --criteria <path> --results <path>
```

**Arguments:**
- `--criteria` (required): Path to criteria JSON file
- `--results` (required): Path to search results JSON file

**Example:**
```bash
python scripts/present_recommendations.py \
  --criteria .cache/criteria.json \
  --results .cache/search_results.json
```

### Input Format

**Two input files:**

1. **Criteria file** (`--criteria`): Conforms to `schemas/user-profile.schema.json`
2. **Results file** (`--results`): JSON array of book candidates with `similarity` scores

### Output Format

**Stdout:** Markdown formatted recommendations

**Spanish Example:**
```markdown
### Mejor Elección
**Neuromancer** de William Gibson

Perfecto para ti porque combina cyberpunk y distopía, con un ritmo rápido y complejidad narrativa.

---

### Descubrimiento
**The Left Hand of Darkness** de Ursula K. Le Guin

Algo diferente, pero explora temas sociopolíticos desde un ángulo único que te sorprenderá.

---

### Desde Otra Categoría
**The Name of the Wind** de Patrick Rothfuss

Como disfrutas la ciencia ficción compleja, esta fantasía narrativa te cautivará con su construcción de mundo.

---

¿Quieres saber más sobre alguno de estos libros? ¿O prefieres que busque algo diferente?
```

**Stderr:** JSON metrics log
```json
{"tokens_used": 1180, "model": "claude-sonnet-4-20250514", "time_ms": 2340, "validation": "passed"}
```

### Implementation Details

**API Configuration:**
- Model: `claude-sonnet-4-20250514`
- Max tokens: 4000
- Temperature: 0.7 (balanced creativity for explanations)
- API key: From `ANTHROPIC_API_KEY` environment variable

**System Prompt Components:**
1. Full content of `.claude/agents/recommendation-presenter.md` (selection rules)
2. JSON schema from `schemas/recommendation.schema.json`
3. Template from `prompts/recommendation-format.md`

**User Message:**
- User criteria JSON
- Search results JSON
- Instruction to select 3 books and format response

**Selection Logic:**

| Slot | Pool | Criterion | Tone |
|------|------|-----------|------|
| **Best Match** | Books where `genre == primary_genre` | Highest similarity | Confident |
| **Discovery** | Same pool, excluding Best Match | Lowest trope overlap (novelty), min similarity 0.6 | Intriguing |
| **Secondary Match** | Books where `genre` in `secondary_genres` | Highest similarity | Bridge-building |

**Response Parsing:**
1. Split on first markdown header (`###` or `# `)
2. First part: JSON (validate against schema)
3. Second part: Markdown output

**Error Handling:**
- Missing input files → Exit with error
- API errors → Exit with error message
- JSON parsing errors → Exit with error
- Schema validation errors → Exit with error

### Token Consumption
- **Average:** ~1,200 tokens per request
- **Breakdown:**
  - Input tokens: ~600 (system prompt + user message with candidates)
  - Output tokens: ~600 (JSON + markdown)

### Bilingual Support
- **Language detection:** Reads `interaction_language` from criteria JSON
- **Template selection:** Spanish vs. English markdown template
- **Explanations:** Written in user's interaction language

---

## Testing

### End-to-End Test Suite

**Script:** `scripts/test_pipeline.py`

**Usage:**
```bash
python scripts/test_pipeline.py
```

**Test Cases:**
1. **Spanish input:** "Me gusta la ciencia ficción hard y las distopías. Leí 1984 y Fundación."
   - Expected: `primary_genre: "sci-fi"`, `interaction_language: "es"`
   - Validates Spanish markdown output

2. **English input:** "I love dark fantasy with morally gray characters. I've read The Poppy War."
   - Expected: `primary_genre: "fantasy"`, `interaction_language: "en"`
   - Validates English markdown output

**Validation Steps:**
- Schema validation for criteria JSON
- Schema validation for recommendations JSON
- Token consumption measurement
- Language-specific markdown markers verification

**Exit Codes:**
- 0: All tests passed
- 1: One or more tests failed

---

## Token Optimization Strategies

### Why This Architecture?

**Before (inline execution):**
- Claude reads extraction rules, processes user input, generates criteria → ~1,500 tokens
- Vector search (external script) → 0 tokens
- Claude reads presentation rules, selects books, generates markdown → ~2,000 tokens
- **Total:** ~3,500 tokens per request

**After (tool-based):**
- Extract profile (Haiku API with rules) → ~500 tokens
- Vector search (external script) → 0 tokens
- Present recommendations (Sonnet API with rules) → ~1,200 tokens
- **Total:** ~1,700 tokens per request

**Savings:** ~51% reduction

### Cost Analysis

**Per request cost:**
- Haiku: 500 tokens @ $0.25/MTok = $0.000125
- Sonnet: 1,200 tokens @ $3/MTok = $0.0036
- **Total:** ~$0.00375 per recommendation request

**Comparison to inline:**
- Inline (Sonnet): 3,500 tokens @ $3/MTok = $0.0105
- **Savings:** ~64% cost reduction

### Latency Profile

**Total pipeline latency:** ~3-5 seconds

**Breakdown:**
- extract_profile API call: ~1-2 seconds
- vector_search local execution: ~500ms
- present_recommendations API call: ~2-3 seconds

**Bottleneck:** API calls (network latency + model execution)

---

## Schema Validation

All JSON inputs and outputs are validated against JSON Schema (draft-07) files:

### User Profile Schema
**File:** `schemas/user-profile.schema.json`

**Required fields:**
- `primary_genre` (enum: 6 genres)
- `language_preference` (enum: es, en, any)
- `interaction_language` (enum: es, en)

**Validation library:** `jsonschema` (Python package)

### Recommendation Schema
**File:** `schemas/recommendation.schema.json`

**Required fields:**
- `best_match`, `discovery`, `secondary_match` (Recommendation objects)
- `metadata` (total_candidates_evaluated, primary_genre, secondary_genre_used, interaction_language)

**Recommendation object structure:**
- `book` (id, title, author, genre + optional synopsis/cover_url)
- `type` (enum: best_match, discovery, secondary_match)
- `score` (float 0.0-1.0)
- `explanation` (string, in user's language)
- `match_reasons` (array of "domain:value" strings)

---

## Error Handling Patterns

### extract_profile.py

```python
# API errors
except anthropic.APIError as e:
    return {"status": "error", "message": f"API error: {str(e)}"}

# JSON parsing errors
except json.JSONDecodeError as e:
    return {"status": "error", "message": f"Invalid JSON from API: {str(e)}"}

# Schema validation errors
except jsonschema.ValidationError as e:
    return {"status": "error", "message": f"Schema validation failed: {e.message}"}
```

### vector_search.py

```python
# No results
if not filtered:
    print("⚠️  No books match the criteria", file=sys.stderr)
    print(json.dumps([]))
    sys.exit(0)

# Missing catalog
if not catalog_path.exists():
    print(f"❌ Error: Catalog with embeddings not found", file=sys.stderr)
    sys.exit(1)
```

### present_recommendations.py

```python
# Missing input files
if not Path(criteria_path).exists():
    return {"status": "error", "message": f"Criteria file not found: {criteria_path}"}

# Response parsing errors
except ValueError as e:
    return {"status": "error", "message": f"Failed to parse response: {str(e)}"}
```

---

## Dependencies

**File:** `requirements.txt`

```
anthropic>=0.18.0      # Official Anthropic SDK
sentence-transformers  # For embedding generation
numpy                  # For vector operations
jsonschema             # For schema validation
```

**Installation:**
```bash
pip install -r requirements.txt
```

**Environment Variables:**
- `ANTHROPIC_API_KEY` (required): API key for Anthropic services

---

## Future Optimizations

### Potential Improvements

1. **Caching:**
   - Cache genre mapping and adjacency JSON in memory (avoid repeated file reads)
   - Cache sentence-transformers model globally in present_recommendations.py

2. **Batch Processing:**
   - Support multiple user inputs in a single extract_profile call
   - Amortize API overhead across multiple requests

3. **Parallel Execution:**
   - Run extract_profile and vector_search concurrently (requires pre-caching criteria)

4. **Model Selection:**
   - Use even smaller model for extraction (e.g., claude-haiku-lite if available)
   - Experiment with lower temperature for present_recommendations (reduce creativity for cost)

5. **Streaming:**
   - Use streaming API for present_recommendations to show progressive markdown output
   - Reduce perceived latency

---

## Troubleshooting

### Common Issues

**Issue:** `ANTHROPIC_API_KEY environment variable not set`
- **Solution:** Set the environment variable: `export ANTHROPIC_API_KEY=your_key_here` (Linux/Mac) or `set ANTHROPIC_API_KEY=your_key_here` (Windows)

**Issue:** `Catalog with embeddings not found`
- **Solution:** Run `python scripts/generate_embeddings.py` to generate `data/catalog_with_embeddings.json`

**Issue:** Schema validation failed
- **Solution:** Check that the API response matches the expected schema. Review the error message for specific field issues.

**Issue:** No results returned from vector_search
- **Solution:** Criteria may be too restrictive (e.g., all books in primary_genre are in books_read). Try different preferences.

**Issue:** ModuleNotFoundError: No module named 'anthropic'
- **Solution:** Install dependencies: `pip install -r requirements.txt`

---

## Appendix: File Structure

```
.
├── .cache/                          # Temporary runtime files (gitignored)
│   ├── criteria.json               # User profile from extract_profile
│   └── search_results.json         # Candidates from vector_search
│
├── .claude/
│   └── agents/
│       ├── profile-extractor.md    # Extraction rules (reference only)
│       └── recommendation-presenter.md  # Presentation rules (reference only)
│
├── data/
│   ├── catalog_with_embeddings.json  # Book catalog with pre-computed embeddings
│   ├── genre-mapping.json           # Spanish→English genre normalization
│   └── genre-adjacency.json         # Genre adjacency relationships
│
├── docs/
│   └── tools-documentation.md       # This file
│
├── prompts/
│   └── recommendation-format.md     # Markdown display templates (ES/EN)
│
├── schemas/
│   ├── user-profile.schema.json     # Criteria validation schema
│   └── recommendation.schema.json   # Output validation schema
│
├── scripts/
│   ├── extract_profile.py           # Tool 1: Profile extraction
│   ├── vector_search.py             # Tool 2: Similarity search
│   ├── present_recommendations.py   # Tool 3: Recommendation presentation
│   └── test_pipeline.py             # End-to-end test suite
│
├── requirements.txt                 # Python dependencies
├── CLAUDE.md                        # Project documentation
└── .gitignore                       # Git ignore patterns
```
