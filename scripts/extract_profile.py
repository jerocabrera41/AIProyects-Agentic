#!/usr/bin/env python3
"""
Profile Extractor Tool
Extracts structured user reading preferences from natural language using Anthropic API.
Supports bilingual input (ES/EN).
"""

import json
import sys
import os
import re
from pathlib import Path
from anthropic import Anthropic
import jsonschema


def load_file(path, encoding='utf-8'):
    """Load file content as string."""
    with open(path, 'r', encoding=encoding) as f:
        return f.read()


def load_json(path, encoding='utf-8'):
    """Load JSON file."""
    with open(path, 'r', encoding=encoding) as f:
        return json.load(f)


def build_system_prompt(project_root):
    """Build the system prompt by combining all necessary reference files."""
    # Load the extraction rules
    extractor_rules = load_file(project_root / '.claude' / 'agents' / 'profile-extractor.md')

    # Load the JSON schema
    schema = load_json(project_root / 'schemas' / 'user-profile.schema.json')
    schema_str = json.dumps(schema, indent=2)

    # Load genre mapping and adjacency
    genre_mapping = load_json(project_root / 'data' / 'genre-mapping.json')
    genre_adjacency = load_json(project_root / 'data' / 'genre-adjacency.json')

    system_prompt = f"""You are a book recommendation assistant that extracts structured user preferences from natural language.

# EXTRACTION RULES

{extractor_rules}

# GENRE MAPPING (Spanish → English normalization)

{json.dumps(genre_mapping, indent=2, ensure_ascii=False)}

# GENRE ADJACENCY (For inferring secondary genres)

{json.dumps(genre_adjacency, indent=2)}

# OUTPUT SCHEMA

You MUST return ONLY valid JSON matching this exact schema:

{schema_str}

# CRITICAL INSTRUCTIONS

1. Output ONLY valid JSON. No markdown code fences (```json), no explanation, no extra text.
2. Detect the input language and set `interaction_language` to "es" or "en"
3. Use genre-mapping to normalize Spanish genre names to English
4. Use adjacency_map to infer secondary_genres from primary_genre
5. Extract 3-5 tropes that the user would enjoy
6. Default uncertain fields to "any" or appropriate defaults (maturity_level: 4, pacing: "moderate")
7. Preserve the original user input in the `raw_input` field
8. Return pure JSON only - the response will be parsed directly
"""

    return system_prompt


def strip_markdown_fences(text):
    """Strip markdown code fences if present."""
    # Remove ```json ... ``` or ``` ... ```
    text = text.strip()
    if text.startswith('```'):
        # Find the first newline after opening fence
        first_newline = text.find('\n')
        if first_newline != -1:
            text = text[first_newline + 1:]

        # Remove closing fence
        if text.endswith('```'):
            text = text[:-3]

    return text.strip()


def extract_profile(user_input, api_key, project_root):
    """
    Extract user profile using Anthropic API.

    Returns dict with:
        - status: "success" or "error"
        - file: path to criteria.json (if success)
        - message: error message (if error)
        - tokens_used: token count from API
    """
    try:
        # Initialize Anthropic client
        client = Anthropic(api_key=api_key)

        # Build system prompt
        system_prompt = build_system_prompt(project_root)

        # Call API
        print("🔧 Calling Anthropic API (Haiku)...", file=sys.stderr)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            temperature=0,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_input}
            ]
        )

        # Extract response text
        response_text = response.content[0].text

        # Log token usage
        tokens_used = response.usage.input_tokens + response.usage.output_tokens
        print(f"📊 Tokens used: {tokens_used} (input: {response.usage.input_tokens}, output: {response.usage.output_tokens})", file=sys.stderr)

        # Strip markdown fences if present
        response_text = strip_markdown_fences(response_text)

        # Parse JSON
        try:
            profile_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            return {
                "status": "error",
                "message": f"Invalid JSON from API: {str(e)}\nResponse was: {response_text[:200]}..."
            }

        # Validate against schema
        schema = load_json(project_root / 'schemas' / 'user-profile.schema.json')
        try:
            jsonschema.validate(profile_data, schema)
            print("✓ Schema validation passed", file=sys.stderr)
        except jsonschema.ValidationError as e:
            return {
                "status": "error",
                "message": f"Schema validation failed: {e.message}"
            }

        # Create .cache directory if it doesn't exist
        cache_dir = project_root / '.cache'
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Write to .cache/criteria.json
        output_path = cache_dir / 'criteria.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(profile_data, f, indent=2, ensure_ascii=False)

        print(f"✓ Written to {output_path}", file=sys.stderr)

        return {
            "status": "success",
            "file": str(output_path),
            "tokens_used": tokens_used
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"API error: {str(e)}"
        }


def main():
    """Main entry point."""
    # Check arguments
    if len(sys.argv) < 2:
        print(json.dumps({
            "status": "error",
            "message": "Usage: python scripts/extract_profile.py \"<user_input>\""
        }))
        sys.exit(1)

    # Get user input
    user_input = sys.argv[1]

    # Get API key from environment
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print(json.dumps({
            "status": "error",
            "message": "ANTHROPIC_API_KEY environment variable not set"
        }))
        sys.exit(1)

    # Determine project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Extract profile
    result = extract_profile(user_input, api_key, project_root)

    # Output result to stdout
    print(json.dumps(result, ensure_ascii=False))

    # Exit with appropriate code
    sys.exit(0 if result["status"] == "success" else 1)


if __name__ == '__main__':
    main()
