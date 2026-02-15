# Agente Recomendador de Libros

Sistema de recomendacion de libros con arquitectura híbrida AI/programática que combina extraccion de perfil con Claude (Haiku), busqueda vectorial semantica con Python, y presentacion personalizada con IA. Logra **80% de reduccion en consumo de tokens** (8,500 → 1,700 tokens/recomendacion) mediante embeddings de 384 dimensiones y busqueda por similitud coseno.

## Que hace

Dado input conversacional en espanol o ingles sobre gustos literarios, genera 3 recomendaciones:

1. **Mejor Eleccion** - El mejor match para tu categoria principal
2. **Descubrimiento** - Algo que no sabias que querias leer
3. **Categoria Secundaria** - El mejor match de un genero adyacente

## Requisitos

- **Claude Code CLI** con suscripcion activa (no requiere API key separada)
- **Python 3.8+** con dependencias:
  - `sentence-transformers` (~500MB descarga inicial)
  - `numpy`

Ver [docs/installation.md](docs/installation.md) para guia completa de instalacion.

## Estructura del Proyecto

```
.
├── CLAUDE.md                              # Instrucciones de orquestacion del sistema
├── .claude/
│   └── agents/
│       ├── profile-extractor.md           # Extrae perfil del usuario (Haiku, ~500 tokens)
│       └── book-recommender.md            # Presenta recomendaciones finales
├── scripts/
│   ├── generate_embeddings.py             # Genera embeddings de 384-dim (one-time)
│   ├── vector_search.py                   # Busqueda semantica (0 tokens)
│   └── README.md                          # Documentacion tecnica de scripts
├── data/
│   ├── catalog.json                       # Catalogo curado de 30 libros
│   ├── catalog_with_embeddings.json       # Catalogo + embeddings (213KB)
│   ├── genre-mapping.json                 # Mapeo ES/EN de generos
│   └── genre-adjacency.json               # Relaciones entre generos
├── schemas/
│   ├── user-profile.schema.json           # Schema del perfil de usuario
│   ├── book-entry.schema.json             # Schema de libro con embeddings
│   └── recommendation.schema.json         # Schema del resultado
├── prompts/
│   ├── greeting.md                        # Saludo inicial bilingue
│   ├── follow-up-questions.md             # Preguntas de clarificacion
│   └── recommendation-format.md           # Template de presentacion
├── docs/
│   ├── installation.md                    # Guia de instalacion Python + dependencias
│   ├── token-optimization-analysis.md     # Analisis de reduccion de tokens
│   └── architecture.md                    # Arquitectura detallada del sistema
└── README.md
```

## Como Usar

### 1. Instalacion (One-time Setup)

```bash
# Instalar dependencias Python
pip install sentence-transformers numpy

# Generar embeddings para catalogo
cd "C:\Users\jeroc\Proyectos AI\Test1- Agente Recomendador de Libros"
python scripts/generate_embeddings.py

# Output: data/catalog_with_embeddings.json (~213KB)
```

Ver [docs/installation.md](docs/installation.md) para guia detallada.

### 2. Iniciar sesion de Claude

```bash
cd "C:\Users\jeroc\Proyectos AI\Test1- Agente Recomendador de Libros"
claude
```

Verificar agentes cargados con `/agents`:
- profile-extractor (Haiku)
- book-recommender

### 3. Describir preferencias

Simplemente describe que tipo de libro buscas:

```
Me gusta la ciencia ficcion, especialmente historias sobre inteligencia
artificial y el futuro. He leido Dune y me encanto. Busco algo reflexivo.
```

O en ingles:

```
I love dark fantasy and horror. Looking for something complex and intense.
```

### 4. Flujo del Sistema (3 pasos, ~1,700 tokens)

1. **profile-extractor (Haiku)** → Extrae criterios (genero, tropes, mood, pacing) → JSON (~500 tokens)
2. **Python vector_search.py** → Filtra + busqueda semantica → Top 10 candidatos (0 tokens)
3. **Claude** → Lee top 10 + genera 3 recomendaciones personalizadas (~1,200 tokens)

**Resultado**: 3 recomendaciones con explicaciones detalladas en tu idioma.

## Generos Soportados (MVP)

| Genero             | Clave              | Libros en catalogo |
|--------------------|--------------------|--------------------|
| Ciencia Ficcion    | sci-fi             | 5                  |
| Fantasia           | fantasy            | 5                  |
| Thriller           | thriller           | 5                  |
| Romance            | romance            | 5                  |
| Terror             | horror             | 5                  |
| Ficcion Literaria  | literary-fiction   | 5                  |

## Arquitectura: Vector Search Hibrida

### Por que Vector Search?

**Problema original**: Arquitectura basada 100% en agentes consumia **8,500 tokens/recomendacion** (~15-20 recomendaciones por sesion).

**Solucion**: Arquitectura hibrida que combina IA (extraccion + presentacion) con programacion (filtrado + busqueda):

```
Usuario → profile-extractor (Haiku, 500T) → vector_search.py (0T) → Claude presenta (1,200T)
Total: ~1,700 tokens/recomendacion (~115 recomendaciones/sesion)
```

### Beneficios

| Metrica | Antes (Agentes) | Despues (Vector Search) | Mejora |
|---------|-----------------|-------------------------|--------|
| **Tokens/recomendacion** | 8,500 | 1,700 | **-80%** |
| **Recomendaciones/sesion** | 15-20 | ~115 | **6-8x** |
| **Escalabilidad** | 30-100 libros | 10,000+ libros | **100x+** |
| **Latencia** | Variable | 1-2s (vector search) | Constante |

### Como Funciona

1. **Embeddings pre-generados**: Cada libro del catalogo tiene un vector de 384 dimensiones que captura:
   - Contenido semantico (titulo, autor, sinopsis)
   - Metadata narrativa (tropes, mood, pacing)
   - Clasificacion (genero, subgeneros, maturity_level)

2. **Filtrado programatico**: Sin consumir tokens, el script Python:
   - Filtra por genero exacto
   - Filtra por nivel de madurez apropiado
   - Excluye libros ya leidos
   - Filtra por idioma (si especificado)

3. **Busqueda semantica**: Calcula similitud coseno entre:
   - Query embedding (generado desde criterios del usuario)
   - Embeddings de libros filtrados
   - Retorna top 10 mas similares

4. **Presentacion con IA**: Claude lee top 10 y genera 3 recomendaciones:
   - **Best Match**: Mayor similitud en genero principal
   - **Discovery**: Alta novedad (tropes nuevos) + buena similitud
   - **Secondary Match**: Mejor en genero adyacente

Ver [docs/token-optimization-analysis.md](docs/token-optimization-analysis.md) para analisis completo.

## Expandir el Catalogo

Para agregar libros al catalogo:

1. **Editar** `data/catalog.json` siguiendo el schema en `schemas/book-entry.schema.json`

   Campos **requeridos** para vector search:
   - `id`, `title`, `author`, `genre`, `language` (basicos)
   - `maturity_level` (1-5): Nivel de madurez apropiado
   - `tropes` (array 3-5): Elementos narrativos (ej: "dystopian-society", "chosen-one")
   - `mood` (array 1-3): Tonos (ej: "dark", "tense", "hopeful")
   - `pacing` (string): Ritmo de lectura ("slow", "moderate", "fast")
   - `synopsis` (string): Resumen de 100-300 caracteres

2. **Re-generar embeddings**:
   ```bash
   python scripts/generate_embeddings.py
   ```

   Esto actualiza `data/catalog_with_embeddings.json` con los nuevos libros.

3. **Listo**: El sistema automaticamente usara los embeddings actualizados en la proxima busqueda.

**Nota**: Los embeddings capturan la semantica completa del libro. Cuanto mas rica la metadata (tropes, mood, synopsis), mejores las recomendaciones.
