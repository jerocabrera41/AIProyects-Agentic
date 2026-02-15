# Arquitectura del Sistema

## Vision General

Sistema de recomendacion de libros que usa 2 subagentes de Claude Code orquestados por una conversacion principal (lead). El flujo es secuencial: extraer perfil -> buscar y recomendar (un solo paso).

## Diagrama de Flujo

```
Usuario (ES/EN)
    |
    v
[Main Conversation / Lead]  <-- lee CLAUDE.md automáticamente
    |
    | 1. Saluda y recibe input conversacional
    | 2. Si input es vago, pide clarificación (prompts/follow-up-questions.md)
    | 3. Si hay suficiente info, delega a profile-extractor
    v
[profile-extractor] (haiku, sin tools)
    |  Analiza texto natural del usuario
    |  Detecta idioma (ES/EN)
    |  Extrae: género, temas, mood, complejidad, libros leídos
    |  Output: UserProfile JSON (~500 tokens)
    v
[Main Conversation]
    |
    | 4. Recibe UserProfile, ejecuta vector_search.py
    | 5. Bash: python scripts/vector_search.py /tmp/criteria.json > top_10.json
    v
[vector_search.py] (Python local, 0 tokens)
    |  Carga data/catalog_with_embeddings.json
    |  Aplica filtros programáticos:
    |    - Genre (primary_genre)
    |    - Maturity level (maturity_level)
    |    - Language (language_preference)
    |    - Books read (excluye books_read)
    |  Genera embedding de query (tropes + mood + pacing + themes)
    |  Calcula cosine similarity contra catálogo
    |  Output: Top 10 candidatos ordenados por similarity score
    v
[Main Conversation]
    |
    | 6. Invoca recommendation-presenter con top_10.json + user profile
    v
[recommendation-presenter] (haiku, Read)
    |  Lee top_10.json y user profile
    |  Selecciona 3 libros (Best Match / Discovery / Secondary Match)
    |  Genera explicaciones personalizadas
    |  Formatea según prompts/recommendation-format.md
    |  Output: JSON + Markdown (~1,200 tokens)
    v
[Main Conversation]
    |
    | 7. Presenta markdown al usuario
    | 8. Pregunta si quiere más detalles o nuevas recomendaciones
    v
Usuario recibe 3 recomendaciones personalizadas

Total consumo: ~1,700 tokens por recomendación
```

## Componentes

### profile-extractor (Subagente)
- **Archivo**: `.claude/agents/profile-extractor.md`
- **Modelo**: Haiku (rápido, tarea estructurada)
- **Tools**: Ninguno
- **Responsabilidad**: Convertir texto natural a UserProfile JSON
- **Consumo**: ~500 tokens
- **Por qué separado**: Tarea limpia de NLP que se beneficia de un prompt enfocado sin ruido de datos de catálogo

### vector_search.py (Script Python)
- **Archivo**: `scripts/vector_search.py`
- **Modelo**: all-MiniLM-L6-v2 (sentence-transformers, local)
- **Dependencias**: numpy, scikit-learn, sentence-transformers
- **Responsabilidad**:
  - Filtrar catálogo por género, madurez, idioma, libros leídos
  - Generar embedding de query desde criterios de usuario
  - Calcular cosine similarity contra embeddings pre-generados
  - Retornar top-10 candidatos ordenados
- **Consumo**: 0 tokens (ejecución local, sin LLM de Claude)
- **Por qué separado**: Elimina 6,800 tokens de búsqueda iterativa que hacía book-recommender con Open Library API

### Main Conversation (Claude Principal)
- **Modelo**: Sonnet 4.5
- **Responsabilidad**:
  - Orquestar flujo completo
  - Ejecutar `python scripts/vector_search.py` vía Bash
  - Invocar recommendation-presenter con top_10.json y user profile
  - Presentar markdown formateado al usuario
- **Consumo**: ~200 tokens (solo orquestación, sin lógica de presentación)

### recommendation-presenter (Subagente)
- **Archivo**: `.claude/agents/recommendation-presenter.md`
- **Modelo**: Haiku (rápido, tarea estructurada)
- **Tools**: Read
- **Responsabilidad**:
  - Leer top_10.json y user profile JSON
  - Seleccionar 3 libros con lógica de Best Match / Discovery / Secondary Match
  - Generar explicaciones personalizadas en idioma del usuario
  - Formatear según prompts/recommendation-format.md
- **Consumo**: ~1,200 tokens
- **Por qué separado**: Separa orquestación (Main) de presentación (agente). Prompt especializado en selección y tone.

## Schemas de Datos

Los tres schemas JSON en `schemas/` definen el contrato de datos entre agentes:

1. **UserProfile** (`user-profile.schema.json`): profile-extractor -> book-recommender
2. **BookEntry** (`book-entry.schema.json`): catalog.json -> book-recommender (uso interno)
3. **RecommendationResult** (`recommendation.schema.json`): book-recommender -> main conversation

## Lógica de Vector Search

### Filtrado Programático (Python)
El script aplica 4 filtros antes de calcular similarity:

| Filtro | Criterio | Ejemplo |
|--------|----------|---------|
| **Genre** | Coincide con `primary_genre` o `secondary_genres` | "sci-fi" → solo libros sci-fi/fantasy |
| **Maturity** | `book.maturity_level >= user.maturity_level` | Usuario nivel 3 → libros 3, 4, 5 |
| **Language** | `book.language` en ["both", user.language] | Usuario "es" → libros ES o "both" |
| **Not Read** | `book.id` NO en `user.books_read` | Excluye libros ya leídos |

### Similarity Scoring
1. **Query embedding**: Se construye texto desde `tropes + mood + pacing + themes_liked` del usuario
2. **Vectorización**: `all-MiniLM-L6-v2` genera embedding de 384 dimensiones
3. **Cosine similarity**: Distancia coseno entre query y cada embedding de libro pre-generado
4. **Ranking**: Top-10 libros con mayor similarity score (0.0 - 1.0)

### Selección de 3 Recomendaciones (Claude Principal)
Claude lee `top_10.json` y aplica lógica final:

1. **Best Match**: Libro con highest similarity score en `primary_genre`
2. **Discovery**:
   - Alta **novelty**: Libro con tropes NO presentes en `themes_liked` del usuario
   - Buena **similarity**: Score >= 0.6
   - Bonus: Tags "underrated", "cult-classic", "award-winner"
3. **Secondary Match**: Highest similarity score en género adyacente (ver `data/genre-adjacency.json`)

Deduplicación: Ningún libro aparece en más de una posición.

## Mapa de Adyacencia de Generos

```
sci-fi <-------> fantasy
  |                 |
  v                 v
literary-fiction   horror
  ^                 ^
  |                 |
romance <-------> (via literary-fiction)
thriller <------> horror
thriller <------> literary-fiction
romance <-------> fantasy
```

literary-fiction es adyacente a todos los generos.
