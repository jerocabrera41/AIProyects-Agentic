# Arquitectura del Sistema

## Vision General

Sistema de recomendacion de libros que usa 2 subagentes de Claude Code orquestados por una conversacion principal (lead). El flujo es secuencial: extraer perfil -> buscar y recomendar (un solo paso).

## Diagrama de Flujo

```
Usuario (ES/EN)
    |
    v
[Main Conversation / Lead]  <-- lee CLAUDE.md automaticamente
    |
    | 1. Saluda y recibe input conversacional
    | 2. Si input es vago, pide clarificacion (prompts/follow-up-questions.md)
    | 3. Si hay suficiente info, delega a profile-extractor
    v
[profile-extractor] (sonnet, sin tools)
    |  Analiza texto natural del usuario
    |  Detecta idioma (ES/EN)
    |  Extrae: genero, temas, mood, complejidad, libros leidos
    |  Output: UserProfile JSON
    v
[Main Conversation]
    |
    | 4. Recibe UserProfile, delega a book-recommender
    v
[book-recommender] (sonnet, Bash+Read+Glob+Grep)
    |  Lee data/catalog.json (catalogo local curado)
    |  Filtra por genero y excluye libros leidos
    |  Busca en Open Library API via curl
    |  Merge: local (alta prioridad) + API (baja prioridad)
    |  Scoring multidimensional de cada candidato
    |  Selecciona 3 recomendaciones:
    |    - Best Match: mayor score en genero principal
    |    - Discovery: balance novedad/relevancia en mismo genero
    |    - Secondary Match: mejor de genero adyacente
    |  Output: RecommendationResult JSON
    v
[Main Conversation]
    |
    | 5. Formatea segun prompts/recommendation-format.md
    | 6. Presenta al usuario en su idioma
    | 7. Pregunta si quiere mas detalles o nuevas recomendaciones
    v
Usuario recibe 3 recomendaciones personalizadas
```

## Subagentes

### profile-extractor
- **Archivo**: `.claude/agents/profile-extractor.md`
- **Modelo**: Sonnet (rapido, tarea estructurada)
- **Tools**: Ninguno
- **Responsabilidad**: Convertir texto natural a UserProfile JSON
- **Por que separado**: Tarea limpia de NLP que se beneficia de un prompt enfocado sin ruido de datos de catalogo

### book-recommender
- **Archivo**: `.claude/agents/book-recommender.md`
- **Modelo**: Sonnet (rapido, buena relacion velocidad/calidad)
- **Tools**: Bash (curl para API), Read, Glob, Grep
- **Responsabilidad**: Buscar candidatos (catalogo local + Open Library API), scoring multidimensional, y seleccion de 3 recomendaciones con explicaciones personalizadas
- **Por que fusionado**: Elimina un round-trip completo entre agentes. Un catalogo de ~30 libros no justifica un agente separado de busqueda. Sonnet es suficiente para el scoring y las explicaciones, reduciendo latencia vs Opus sin perder calidad significativa.

## Schemas de Datos

Los tres schemas JSON en `schemas/` definen el contrato de datos entre agentes:

1. **UserProfile** (`user-profile.schema.json`): profile-extractor -> book-recommender
2. **BookEntry** (`book-entry.schema.json`): catalog.json -> book-recommender (uso interno)
3. **RecommendationResult** (`recommendation.schema.json`): book-recommender -> main conversation

## Logica de Scoring

El recommendation-engine evalua candidatos en 6 dimensiones ponderadas:

| Dimension        | Peso | Descripcion                          |
|------------------|------|--------------------------------------|
| Genre match      | 30%  | Coincidencia de genero principal     |
| Theme overlap    | 25%  | Temas compartidos                    |
| Mood alignment   | 15%  | Tono emocional compatible            |
| Complexity fit   | 10%  | Nivel de lectura adecuado            |
| Language match   | 10%  | Disponible en idioma preferido       |
| Not already read | 10%  | No ha sido leido (descalifica si ya) |

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
