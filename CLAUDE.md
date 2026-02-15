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
YO (Claude principal) leo top_10.json y genero 3 recomendaciones:
1. **Best Match**: Highest similarity en primary genre
2. **Discovery**: Alta novelty (tropes NO en user profile) + good similarity
3. **Secondary Match**: Best en género adyacente o secondary_genres

Formatear usando `prompts/recommendation-format.md`
- Idioma: usar `interaction_language` del perfil
- Presentar título, autor, score, explicación personalizada
- Consumo: ~1,200 tokens

**Total**: ~1,700 tokens/recomendación (~115 recomendaciones/sesión vs 15-20 actual)

## Géneros (MVP)
sci-fi, fantasy, thriller, romance, horror, literary-fiction

## Convenciones
- IDs de libros: `titulo-autor` (lowercase, hyphens)
- Géneros siempre en inglés kebab-case
- Explicaciones en idioma del usuario
- Subagentes devuelven SOLO JSON

## Referencias
- Agentes: `.claude/agents/`
- Datos: `data/` (catalog.json, genre-mapping.json, genre-adjacency.json)
- Esquemas: `schemas/`
- Prompts: `prompts/`
- Docs: `docs/`
