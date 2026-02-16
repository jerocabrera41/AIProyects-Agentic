# Agente Recomendador de Libros

## Visión General
Sistema de recomendación de libros bilingüe (ES/EN) que genera 3 recomendaciones personalizadas a partir de una conversación natural con el usuario.

## Las 3 Recomendaciones
1. **Best Match** - Mejor libro en categoría principal del usuario
2. **Discovery** - Sorpresa dentro de la misma categoría (algo inesperado)
3. **Secondary Match** - Mejor libro en categoría adyacente

## Available Tools

### 1. extract_profile
**Purpose:** Extract structured criteria from natural language user input

**Invocation:**
```bash
python scripts/extract_profile.py "<user_input>"
```

**Input:** String with user's reading preferences (ES or EN)

**Output:** JSON to stdout
```json
{"status": "success", "file": ".cache/criteria.json", "tokens_used": 520}
```

**Token consumption:** ~500 tokens (Haiku)

**When to use:** Whenever user describes their reading preferences

### 2. vector_search
**Purpose:** Find similar books using cosine similarity on pre-computed embeddings

**Invocation:**
```bash
python scripts/vector_search.py .cache/criteria.json > .cache/search_results.json
```

**Input:** Path to criteria JSON file

**Output:** JSON array of top-15 candidates (10 primary + 5 secondary genre) to stdout

**Token consumption:** 0 tokens (local Python execution)

**When to use:** After extract_profile completes successfully

**Note:** Now returns both primary and secondary genre candidates for comprehensive recommendations

### 3. present_recommendations
**Purpose:** Select 3 personalized recommendations and format output

**Invocation:**
```bash
python scripts/present_recommendations.py \
  --criteria .cache/criteria.json \
  --results .cache/search_results.json
```

**Input:** Two JSON files (criteria + search results)

**Output:** Markdown formatted recommendations to stdout

**Token consumption:** ~1,200 tokens (Sonnet)

**When to use:** After vector_search completes successfully

## Flujo de Orquestación (Tool-Based)

Cuando usuario describe el libro que quiere, ejecuto los 3 pasos usando las tools disponibles:

### Paso 1: Extraer Criterios
```bash
python scripts/extract_profile.py "<user_input>"
```
- Script usa Haiku API para extraer perfil estructurado
- Genera el JSON de criterios (genre, maturity_level, tropes, mood, pacing, books_read)
- Escribe el JSON a `.cache/criteria.json`
- Consumo: **~500 tokens** (Haiku API call)

### Paso 2: Vector Search (Programático - 0 tokens)
```bash
python scripts/vector_search.py .cache/criteria.json > .cache/search_results.json
```
- Filtros aplicados: genre, maturity_level, language, books_read
- Algoritmo: Cosine similarity sobre embeddings pre-generados (384-dim, all-MiniLM-L6-v2)
- Output: Top 15 candidatos (10 primary + 5 secondary) con similarity scores
- Consumo: **0 tokens** (ejecución local Python, sin llamadas a Claude)

### Paso 3: Presentar Recomendaciones
```bash
python scripts/present_recommendations.py \
  --criteria .cache/criteria.json \
  --results .cache/search_results.json
```
- Script usa Sonnet API para seleccionar y formatear recomendaciones
- Aplica lógica de Best Match / Discovery / Secondary Match
- Genera explicaciones personalizadas en el idioma del usuario
- Formatea según `prompts/recommendation-format.md`
- Consumo: **~1,200 tokens** (Sonnet API call)

### Ventajas
- **Token reduction:** ~51% reduction (from ~3,500 to ~1,700 tokens per full pipeline)
- **Cost efficiency:** Haiku for extraction (~$0.13/MTok), Sonnet for presentation (~$3/MTok)
- **Modularity:** Each tool is testable and reusable independently
- **No subagent overhead:** Direct tool invocation via bash commands

## Géneros (MVP)
sci-fi, fantasy, thriller, romance, horror, literary-fiction

## Convenciones
- IDs de libros: `titulo-autor` (lowercase, hyphens)
- Géneros siempre en inglés kebab-case
- Explicaciones en idioma del usuario
- Reglas de extracción y presentación: `.claude/agents/` (referencia, no se invocan como subagentes)

## Referencias
- Agentes: `.claude/agents/`
- Datos: `data/` (catalog.json, genre-mapping.json, genre-adjacency.json)
- Esquemas: `schemas/`
- Prompts: `prompts/`
- Docs: `docs/`
