#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Book Recommendation Wrapper
Executes the full 3-step pipeline in a single command.
"""

import sys
import os
import subprocess
import argparse
import json
from pathlib import Path

# UTF-8 handling for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def run_step(description, command, capture_output=False, verbose=False):
    """
    Run a pipeline step and handle errors.

    Returns:
        tuple: (success: bool, output: str, tokens: int)
    """
    if verbose:
        print(f"🔧 {description}...", file=sys.stderr)

    # Use appropriate encoding for Windows
    encoding = 'cp1252' if sys.platform == 'win32' else 'utf-8'

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding=encoding,
            errors='replace'
        )

        if result.returncode != 0:
            print(f"❌ Error en {description}", file=sys.stderr)
            print(result.stderr, file=sys.stderr)
            return False, None, 0

        # Extract token count from stderr if present
        tokens = 0
        for line in result.stderr.split('\n'):
            if 'Tokens used:' in line or 'tokens_used' in line:
                try:
                    # Try to extract number from "Tokens used: 2569" format
                    if 'Tokens used:' in line:
                        tokens = int(line.split('Tokens used:')[1].split()[0])
                    # Try to extract from JSON format
                    elif 'tokens_used' in line and '{' in line:
                        data = json.loads(line)
                        tokens = data.get('tokens_used', 0)
                except:
                    pass

        if verbose:
            if tokens > 0:
                print(f"✓ {description} completado ({tokens:,} tokens)", file=sys.stderr)
            else:
                print(f"✓ {description} completado", file=sys.stderr)

        return True, result.stdout, tokens

    except Exception as e:
        print(f"❌ Error ejecutando {description}: {str(e)}", file=sys.stderr)
        return False, None, 0


def main():
    parser = argparse.ArgumentParser(
        description='Generate book recommendations from natural language input',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python recommend.py "Me gusta la ciencia ficción hard y las distopías"
  python recommend.py --verbose "Quiero una novela atrapante"
  python recommend.py --quiet "I love dark fantasy"
        """
    )

    parser.add_argument(
        'user_input',
        type=str,
        help='Your reading preferences in natural language (ES or EN)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show progress for each step'
    )

    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress all progress messages, only show recommendations'
    )

    args = parser.parse_args()

    # Validate input
    if not args.user_input or not args.user_input.strip():
        print("❌ Error: Please provide your reading preferences", file=sys.stderr)
        sys.exit(1)

    # Check API key
    if not os.environ.get('ANTHROPIC_API_KEY'):
        print("❌ Error: ANTHROPIC_API_KEY environment variable not set", file=sys.stderr)
        print("   Please set your API key first:", file=sys.stderr)
        print("   - Windows CMD: set ANTHROPIC_API_KEY=your_key_here", file=sys.stderr)
        print("   - Windows PowerShell: $env:ANTHROPIC_API_KEY=\"your_key_here\"", file=sys.stderr)
        print("   - Linux/Mac: export ANTHROPIC_API_KEY=your_key_here", file=sys.stderr)
        sys.exit(1)

    verbose = args.verbose and not args.quiet
    total_tokens = 0

    # Determine project root
    project_root = Path(__file__).parent

    # Step 1: Extract profile
    success, output, tokens = run_step(
        "Extrayendo perfil de usuario",
        f'python "{project_root}/scripts/extract_profile.py" "{args.user_input}"',
        capture_output=True,
        verbose=verbose
    )

    if not success:
        sys.exit(1)

    total_tokens += tokens

    # Parse output to get criteria file path
    try:
        result = json.loads(output)
        if result['status'] != 'success':
            print(f"❌ Error: {result.get('message', 'Unknown error')}", file=sys.stderr)
            sys.exit(1)
        criteria_file = result['file']
    except:
        print("❌ Error: Could not parse extract_profile output", file=sys.stderr)
        sys.exit(1)

    # Step 2: Vector search
    search_results_file = project_root / '.cache' / 'search_results.json'
    success, output, tokens = run_step(
        "Buscando libros similares",
        f'python "{project_root}/scripts/vector_search.py" "{criteria_file}"',
        capture_output=True,
        verbose=verbose
    )

    if not success:
        sys.exit(1)

    total_tokens += tokens

    # Save search results
    try:
        search_results_file.parent.mkdir(parents=True, exist_ok=True)
        with open(search_results_file, 'w', encoding='utf-8') as f:
            f.write(output)
    except Exception as e:
        print(f"❌ Error saving search results: {str(e)}", file=sys.stderr)
        sys.exit(1)

    # Step 3: Present recommendations
    success, markdown, tokens = run_step(
        "Generando recomendaciones",
        f'python "{project_root}/scripts/present_recommendations.py" --criteria "{criteria_file}" --results "{search_results_file}"',
        capture_output=True,
        verbose=verbose
    )

    if not success:
        sys.exit(1)

    total_tokens += tokens

    # Show summary if verbose
    if verbose:
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"Total tokens: {total_tokens:,}", file=sys.stderr)
        cost = (total_tokens / 1_000_000) * 3  # Rough estimate at $3/MTok
        print(f"Costo estimado: ${cost:.4f}", file=sys.stderr)
        print(f"{'='*60}\n", file=sys.stderr)

    # Output recommendations
    print(markdown)


if __name__ == '__main__':
    main()
