# Arquitectura del Sistema

## Vision General

Sistema de recomendacion de libros que usa 3 subagentes de Claude Code orquestados por una conversacion principal (lead). El flujo es secuencial: extraer perfil -> investigar libros -> generar recomendaciones.

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
    | 4. Recibe UserProfile, delega a book-researcher
    v
[book-researcher] (sonnet, Bash+Read+Glob+Grep)
    |  Lee data/catalog.json (catalogo local curado)
    |  Filtra por genero y excluye libros leidos
    |  Busca en Open Library API via curl
    |  Merge: local (alta prioridad) + API (baja prioridad)
    |  Output: CandidateBooks JSON array (max 20)
    v
[Main Conversation]
    |
    | 5. Recibe candidatos, delega a recommendation-engine
    v
[recommendation-engine] (opus, Read+Glob+Grep)
    |  Scoring multidimensional de cada candidato
    |  Selecciona 3 recomendaciones:
    |    - Best Match: mayor score en genero principal
    |    - Discovery: balance novedad/relevancia en mismo genero
    |    - Secondary Match: mejor de genero adyacente
    |  Output: RecommendationResult JSON
    v
[Main Conversation]
    |
    | 6. Formatea segun prompts/recommendation-format.md
    | 7. Presenta al usuario en su idioma
    | 8. Pregunta si quiere mas detalles o nuevas recomendaciones
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

### book-researcher
- **Archivo**: `.claude/agents/book-researcher.md`
- **Modelo**: Sonnet (rapido, I/O-heavy)
- **Tools**: Bash (curl para API), Read, Glob, Grep
- **Responsabilidad**: Buscar y filtrar candidatos de catalogo local + Open Library API
- **Por que separado**: Necesita tools de I/O que deben aislarse de los agentes de razonamiento

### recommendation-engine
- **Archivo**: `.claude/agents/recommendation-engine.md`
- **Modelo**: Opus (razonamiento complejo)
- **Tools**: Read, Glob, Grep
- **Responsabilidad**: Scoring, seleccion de 3 recomendaciones, explicaciones personalizadas
- **Por que Opus**: Requiere juicio subjetivo matizado para "discovery", puentes entre generos, y explicaciones bilingues convincentes

## Schemas de Datos

Los tres schemas JSON en `schemas/` definen el contrato de datos entre agentes:

1. **UserProfile** (`user-profile.schema.json`): profile-extractor -> book-researcher, recommendation-engine
2. **BookEntry** (`book-entry.schema.json`): catalog.json -> book-researcher -> recommendation-engine
3. **RecommendationResult** (`recommendation.schema.json`): recommendation-engine -> main conversation

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
