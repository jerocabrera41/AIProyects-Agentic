#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Recommendation Presenter Tool
Selects 3 personalized recommendations from search results and formats output.
Uses Anthropic API with Sonnet for creative explanations.
"""

import json
import sys
import os
import time
import argparse
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
    # Load the presenter rules
    presenter_rules = load_file(project_root / '.claude' / 'agents' / 'recommendation-presenter.md')

    # Load the JSON schema
    schema = load_json(project_root / 'schemas' / 'recommendation.schema.json')
    schema_str = json.dumps(schema, indent=2)

    # Load the format template
    format_template = load_file(project_root / 'prompts' / 'recommendation-format.md')

    system_prompt = f"""You are a book recommendation assistant that selects and presents personalized recommendations.

# SELECTION AND PRESENTATION RULES

{presenter_rules}

# OUTPUT SCHEMA

The JSON portion of your output MUST match this exact schema:

{schema_str}

# DISPLAY TEMPLATE

{format_template}

# CRITICAL INSTRUCTIONS

1. First, output the JSON object (valid JSON, no markdown fences)
2. Then, output a blank line
3. Then, output the markdown display using the appropriate language template
4. Use the user's `interaction_language` for ALL text in explanations and markdown
5. Be specific and personalized - reference actual user preferences
6. Follow the tone guidelines for each recommendation type (confident, intriguing, bridge-building)
7. Keep explanations to 2-3 sentences maximum
"""

    return system_prompt


def build_user_message(criteria_path, results_path):
    """Build the user message from criteria and results files."""
    criteria = load_json(criteria_path)
    results = load_json(results_path)

    message = f"""Please select 3 books following the rules and format the response.

# USER PROFILE

{json.dumps(criteria, indent=2, ensure_ascii=False)}

# CANDIDATE BOOKS (from vector search)

{json.dumps(results, indent=2, ensure_ascii=False)}

Select the best 3 books following the Best Match, Discovery, and Secondary Match rules.
Output the JSON first, then the markdown display.
"""

    return message


def parse_response(response_text):
    """
    Parse the API response into JSON and markdown parts using robust JSON parsing.

    Uses json.JSONDecoder.raw_decode() to find the exact end of the JSON object,
    treating everything after as markdown. This is immune to markdown formatting
    variations (---, ###, etc.) and doesn't rely on Claude following specific
    output format instructions.

    Returns tuple: (json_data, markdown_text)
    """
    text = response_text.strip()

    # Strip optional leading markdown code fence (```json or ```)
    if text.startswith('```'):
        first_newline = text.find('\n')
        if first_newline != -1:
            text = text[first_newline + 1:]
        text = text.strip()

    # Remove closing fence if present (this should be AFTER the JSON, before markdown)
    # Look for ``` on its own line
    fence_pattern = '\n```\n'
    fence_pos = text.find(fence_pattern)
    if fence_pos != -1:
        # Remove the fence line but keep everything after it (the markdown)
        text = text[:fence_pos] + text[fence_pos + len(fence_pattern):]

    # Find start of JSON object
    json_start = text.find('{')
    if json_start == -1:
        raise ValueError("No JSON object found in response")

    # Use raw_decode to find exact end of JSON
    # This returns (parsed_object, end_position)
    decoder = json.JSONDecoder()
    try:
        json_data, end_index = decoder.raw_decode(text, json_start)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON: {str(e)}\nText: {text[:500]}")

    # Everything after the JSON is markdown
    # end_index is the position AFTER the closing } relative to json_start
    markdown_start = json_start + end_index
    markdown_text = text[markdown_start:].strip()

    return json_data, markdown_text


def present_recommendations(criteria_path, results_path, api_key, project_root):
    """
    Present recommendations using Anthropic API.

    Returns dict with:
        - status: "success" or "error"
        - markdown: the formatted output (if success)
        - message: error message (if error)
        - tokens_used: actual token count from API
        - time_ms: execution time in milliseconds
    """
    start_time = time.time()

    try:
        # Validate input files exist
        if not Path(criteria_path).exists():
            return {
                "status": "error",
                "message": f"Criteria file not found: {criteria_path}"
            }

        if not Path(results_path).exists():
            return {
                "status": "error",
                "message": f"Results file not found: {results_path}"
            }

        # Initialize Anthropic client
        client = Anthropic(api_key=api_key)

        # Build system prompt and user message
        system_prompt = build_system_prompt(project_root)
        user_message = build_user_message(criteria_path, results_path)

        # Call API
        print("🔧 Calling Anthropic API (Sonnet)...", file=sys.stderr)

        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4000,
            temperature=0.7,  # Creative writing needs higher temperature
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )

        # Extract response text
        response_text = response.content[0].text

        # Log token usage
        tokens_used = response.usage.input_tokens + response.usage.output_tokens
        print(f"📊 Tokens used: {tokens_used} (input: {response.usage.input_tokens}, output: {response.usage.output_tokens})", file=sys.stderr)

        # Parse response
        try:
            json_data, markdown_text = parse_response(response_text)
        except ValueError as e:
            return {
                "status": "error",
                "message": f"Failed to parse response: {str(e)}"
            }

        # Validate JSON against schema
        schema = load_json(project_root / 'schemas' / 'recommendation.schema.json')
        try:
            jsonschema.validate(json_data, schema)
            validation_status = "passed"
            print("✓ Schema validation passed", file=sys.stderr)
        except jsonschema.ValidationError as e:
            return {
                "status": "error",
                "message": f"Schema validation failed: {e.message}"
            }

        elapsed_ms = int((time.time() - start_time) * 1000)

        # Log metrics to stderr
        log_data = {
            "tokens_used": tokens_used,
            "model": "sonnet",
            "time_ms": elapsed_ms,
            "validation": validation_status
        }
        print(json.dumps(log_data), file=sys.stderr)

        return {
            "status": "success",
            "markdown": markdown_text,
            "tokens_used": tokens_used,
            "time_ms": elapsed_ms
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"API error: {str(e)}"
        }


def main():
    """Main entry point."""
    # Parse arguments
    parser = argparse.ArgumentParser(description='Present personalized book recommendations')
    parser.add_argument('--criteria', required=True, help='Path to criteria JSON file')
    parser.add_argument('--results', required=True, help='Path to search results JSON file')

    args = parser.parse_args()

    # Get API key from environment
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print(json.dumps({
            "status": "error",
            "message": "ANTHROPIC_API_KEY environment variable not set"
        }), file=sys.stderr)
        sys.exit(1)

    # Determine project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Present recommendations
    result = present_recommendations(args.criteria, args.results, api_key, project_root)

    if result["status"] == "success":
        # Output markdown to stdout
        print(result["markdown"])
        sys.exit(0)
    else:
        # Output error to stderr
        print(f"ERROR: {result['message']}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
