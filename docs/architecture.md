# Arquitectura del Sistema

## Vision General

Sistema de recomendación de libros donde Claude principal ejecuta directamente los 3 pasos (extracción, vector search, presentación), usando archivos en `.claude/agents/` como guías de reglas. Sin overhead de subagentes para máxima eficiencia de tokens.

## Diagrama de Flujo

```
Usuario (ES/EN)
    |
    v
[Main Conversation / Claude Principal]  <-- lee CLAUDE.md automáticamente
    |
    | 1. Saluda y recibe input conversacional
    | 2. Si input es vago, pide clarificación
    v
[Paso 1: Extracción de Criterios - ejecutado por Claude principal]
    |  Lee reglas de .claude/agents/profile-extractor.md
    |  Analiza texto del usuario
    |  Extrae: genre, tropes, mood, maturity_level, books_read
    |  Escribe .cache/criteria.json
    |  Consumo: Incluido en tokens de Claude principal
    v
[Paso 2: Vector Search - Python local]
    |  Bash: python scripts/vector_search.py .cache/criteria.json
    |  Filtra por genre, maturity, language, books_read
    |  Calcula cosine similarity (384-dim embeddings)
    |  Output: Top 10 candidatos a stdout
    |  Consumo: 0 tokens
    v
[Paso 3: Presentación - ejecutado por Claude principal]
    |  Lee reglas de .claude/agents/recommendation-presenter.md
    |  Selecciona 3 libros (Best Match / Discovery / Secondary Match)
    |  Genera explicaciones personalizadas
    |  Formatea según prompts/recommendation-format.md
    |  Consumo: Incluido en tokens de Claude principal
    v
Usuario recibe 3 recomendaciones personalizadas

Total consumo: ~1,700 tokens por recomendación
(vs ~15,000 tokens con invocación de subagentes vía Task tool)
```

## Componentes

### Claude Principal (Main Conversation)
- **Modelo**: Sonnet 4.5
- **Responsabilidad**:
  - Ejecutar los 3 pasos directamente (extracción, vector search, presentación)
  - Leer archivos de referencia en `.claude/agents/` para seguir reglas
  - Orquestar flujo completo sin invocar subagentes
- **Consumo**: ~1,700 tokens totales por recomendación

### Archivos de Referencia en `.claude/agents/`

Estos archivos **NO son agentes invocables**. Son **guías de reglas** que Claude principal lee.

#### profile-extractor.md (Guía de Reglas)
- **Uso**: Claude principal lee este archivo para saber cómo extraer criterios
- **Contenido**: Reglas de extracción, mapeo de géneros, detección de idioma
- **Beneficio**: Reglas centralizadas y reutilizables

#### recommendation-presenter.md (Guía de Reglas)
- **Uso**: Claude principal lee este archivo para saber cómo seleccionar y presentar
- **Contenido**: Lógica de Best Match/Discovery/Secondary Match, formato de explicaciones
- **Beneficio**: Consistencia en tono y estructura de recomendaciones

### vector_search.py (Script Python)
- **Archivo**: `scripts/vector_search.py`
- **Modelo**: all-MiniLM-L6-v2 (sentence-transformers, local)
- **Responsabilidad**:
  - Filtrar catálogo por criterios
  - Calcular cosine similarity
  - Retornar top-10 candidatos
- **Consumo**: 0 tokens (ejecución local)

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
