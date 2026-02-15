# Open Library API - Referencia Rapida

## Endpoints Utilizados

### 1. Search API
Busca libros por tema/genero.

```
GET https://openlibrary.org/search.json?subject={subject}&limit=10&fields=key,title,author_name,first_publish_year,subject,cover_i,language
```

**Parametros utiles**:
- `subject`: tema o genero (e.g., "science_fiction", "fantasy", "thriller")
- `limit`: numero maximo de resultados (usar 10 para MVP)
- `fields`: campos a devolver (reduce tamano de respuesta)
- `language`: filtrar por idioma ("spa" para espanol, "eng" para ingles)
- `q`: busqueda general por texto

**Mapeo de generos a subjects**:
- sci-fi -> "science_fiction"
- fantasy -> "fantasy"
- thriller -> "thriller"
- romance -> "romance"
- horror -> "horror"
- literary-fiction -> "literary_fiction"

**Ejemplo**:
```bash
curl -s "https://openlibrary.org/search.json?subject=science_fiction&limit=10&fields=key,title,author_name,first_publish_year,subject,cover_i,language"
```

**Respuesta** (campos relevantes):
```json
{
  "numFound": 12345,
  "docs": [
    {
      "key": "/works/OL12345W",
      "title": "Book Title",
      "author_name": ["Author Name"],
      "first_publish_year": 2020,
      "subject": ["Science fiction", "Space opera", "Aliens"],
      "cover_i": 1234567,
      "language": ["eng", "spa"]
    }
  ]
}
```

### 2. Works API
Obtiene detalles de un libro especifico por su work key.

```
GET https://openlibrary.org/works/{KEY}.json
```

**Ejemplo**:
```bash
curl -s "https://openlibrary.org/works/OL45804W.json"
```

**Campos utiles de la respuesta**:
- `title`: titulo
- `description`: sinopsis (puede ser string o objeto con `value`)
- `subjects`: array de temas
- `covers`: array de IDs de portada

### 3. Covers API
Construye URLs de portadas a partir del `cover_i` del Search API.

```
https://covers.openlibrary.org/b/id/{cover_i}-{size}.jpg
```

**Tamanos disponibles**:
- `S` - Small (thumbnail)
- `M` - Medium (recomendado para display)
- `L` - Large

**Ejemplo**:
```
https://covers.openlibrary.org/b/id/1234567-M.jpg
```

## Notas Importantes

- **Sin autenticacion**: No requiere API key ni registro
- **Rate limiting**: No documentado oficialmente, pero ser conservador (max 1 request por segundo)
- **Disponibilidad**: La API puede ser lenta en momentos de alta carga
- **Datos inconsistentes**: No todos los libros tienen todos los campos (cover_i, language, etc.)
- **Idioma de subjects**: Los subjects estan generalmente en ingles
- **Fallback**: Si la API falla, el sistema debe funcionar solo con el catalogo local
