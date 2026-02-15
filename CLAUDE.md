# Agente Recomendador de Libros

## Visión General
Sistema de recomendación de libros bilingüe (ES/EN) que genera 3 recomendaciones personalizadas a partir de una conversación natural con el usuario.

## Las 3 Recomendaciones
1. **Best Match** - Mejor libro en categoría principal del usuario
2. **Discovery** - Sorpresa dentro de la misma categoría (algo inesperado)
3. **Secondary Match** - Mejor libro en categoría adyacente

## Flujo de Orquestación

Cuando usuario describe el libro que quiere:

### Paso 1: Extraer Perfil
Invocar `profile-extractor` con texto raw del usuario
- Output: JSON UserProfile (ver `schemas/user-profile.schema.json`)

### Paso 2: Buscar y Recomendar
Invocar `book-recommender` con UserProfile del Paso 1
- Lee: `data/catalog.json`, consulta Open Library API
- Output: JSON RecommendationResult

### Paso 3: Presentar Resultados
Formatear respuesta usando `prompts/recommendation-format.md`
- Idioma: usar `interaction_language` del perfil
- Presentar título, autor, explicación personalizada por cada recomendación

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
