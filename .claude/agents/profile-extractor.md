---
name: profile-extractor
description: Extracts structured user reading preferences from natural language. Supports ES/EN.
model: haiku
---

> **NOTA**: Este archivo es una **guía de reglas**, no un agente invocable.
> Claude principal lee estas reglas para ejecutar el paso correspondiente directamente.
> No se usa Task tool para invocar este archivo como subagente.

Extract reading preferences from user input and return ONLY valid JSON.

## Input
Raw user text (Spanish or English) describing what books they want to read.

## Output JSON
```json
{
  "primary_genre": "sci-fi|fantasy|thriller|romance|horror|literary-fiction",
  "secondary_genres": ["inferred adjacent genres"],
  "themes_liked": ["extracted preferences"],
  "themes_disliked": ["themes to avoid"],
  "mood": ["dark", "tense"],
  "mood_preference": "dark|light|adventurous|reflective|tense|romantic|whimsical|melancholic|any",
  "complexity_preference": "accessible|moderate|challenging|any",
  "language_preference": "es|en|any",
  "maturity_level": 4,
  "tropes": ["dystopian-society", "chosen-one", "political-intrigue"],
  "pacing": "moderate|fast|slow",
  "books_read": ["mentioned titles"],
  "books_liked": ["positive titles"],
  "books_disliked": ["negative titles"],
  "interaction_language": "es|en",
  "raw_input": "original user text"
}
```

## Rules
1. Detect input language → set `interaction_language`
2. Extract primary genre (required). Use `data/genre-mapping.json` spanish_to_english mapping
3. Infer secondary genres from `data/genre-adjacency.json` adjacency_map
4. Extract `maturity_level` (1-5): Infer from user age/preference or default to 4 (adult)
5. Extract `tropes` (3-5 items): Common narrative elements user wants (e.g., "chosen-one", "time-travel", "enemies-to-lovers")
6. Extract `pacing`: slow/moderate/fast (default: "moderate")
7. Extract `mood` as array (1-3 moods): e.g., ["dark", "tense"]
8. For books: infer genre/themes. Add to books_read + books_liked OR books_read + books_disliked
9. Default uncertain fields to "any" or appropriate defaults
10. Be generous with theme/trope extraction (e.g., "viajes en el tiempo" → tropes: ["time-travel"], themes: ["adventure"])
11. `language_preference` = reading language, NOT chat language
12. Return JSON ONLY. No markdown, no explanation.
