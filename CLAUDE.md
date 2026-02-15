# Agente Recomendador de Libros

## Visión General
Sistema de recomendación de libros bilingüe (ES/EN) que genera 3 recomendaciones personalizadas a partir de una conversación natural con el usuario.

## Las 3 Recomendaciones
1. **Best Match** - Mejor libro en categoría principal del usuario
2. **Discovery** - Sorpresa dentro de la misma categoría (algo inesperado)
3. **Secondary Match** - Mejor libro en categoría adyacente

## Flujo de Orquestación (Vector Search)

Cuando usuario describe el libro que quiere:

### Paso 1: Extraer Criterios
Invocar `profile-extractor` (Haiku) con texto raw del usuario
- Output: JSON con genre, maturity_level, tropes, mood, pacing, books_read
- Consumo: ~500 tokens

### Paso 2: Vector Search (Programático - 0 tokens)
YO (Claude principal) ejecuto:
```bash
# 1. Escribir criteria JSON a archivo temporal
echo '$CRITERIA_JSON' > /tmp/criteria.json

# 2. Ejecutar vector search y capturar top-10
python scripts/vector_search.py /tmp/criteria.json > /tmp/top_10.json
```
- Input: JSON del profile-extractor (`/tmp/criteria.json`)
- Filtros aplicados: genre, maturity_level, language, books_read
- Algoritmo: Cosine similarity sobre embeddings pre-generados (384-dim, all-MiniLM-L6-v2)
- Output: Top 10 candidatos con similarity scores (`/tmp/top_10.json`)
- Consumo: **0 tokens** (ejecución local Python, sin llamadas a Claude)

### Paso 3: Presentar Recomendaciones
Invocar `recommendation-presenter` (Haiku) con:
- Input 1: `/tmp/top_10.json` (del vector search)
- Input 2: User profile JSON (del profile-extractor)

El agente:
1. Selecciona 3 libros aplicando lógica de Best Match / Discovery / Secondary Match
2. Genera explicaciones personalizadas en el idioma del usuario
3. Formatea según `prompts/recommendation-format.md`
4. Output: JSON + Markdown para display

Consumo: ~1,200 tokens

**Total**: ~1,700 tokens/recomendación (~115 recomendaciones/sesión vs 15-20 actual)

## Géneros (MVP)
sci-fi, fantasy, thriller, romance, horror, literary-fiction

## Convenciones
- IDs de libros: `titulo-autor` (lowercase, hyphens)
- Géneros siempre en inglés kebab-case
- Explicaciones en idioma del usuario
- Agentes devuelven SOLO JSON (salvo recommendation-presenter que retorna JSON + Markdown)

## Referencias
- Agentes: `.claude/agents/`
- Datos: `data/` (catalog.json, genre-mapping.json, genre-adjacency.json)
- Esquemas: `schemas/`
- Prompts: `prompts/`
- Docs: `docs/`
