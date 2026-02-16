#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
End-to-end pipeline testing for book recommendation system.
Tests both Spanish and English inputs through the full pipeline.
"""

import json
import subprocess
import sys
import os
from pathlib import Path
import jsonschema

# Force UTF-8 output encoding on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


# Test cases
TEST_CASES = [
    {
        "name": "Ciencia Ficción (Español)",
        "input": "Me gusta la ciencia ficción hard y las distopías. Leí 1984 y Fundación.",
        "expected_genre": "sci-fi",
        "expected_language": "es"
    },
    {
        "name": "Dark Fantasy (English)",
        "input": "I love dark fantasy with morally gray characters. I've read The Poppy War.",
        "expected_genre": "fantasy",
        "expected_language": "en"
    }
]


def run_command(cmd, check_return_code=True):
    """
    Run a shell command and return (stdout, stderr, return_code).
    """
    # On Windows, use cp1252 (Windows console default) to properly read Spanish characters
    # On Unix, use utf-8
    encoding = 'cp1252' if sys.platform == 'win32' else 'utf-8'

    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        encoding=encoding,
        errors='replace'  # Replace invalid sequences instead of crashing
    )

    if check_return_code and result.returncode != 0:
        print(f"❌ Command failed: {cmd}", file=sys.stderr)
        print(f"   stderr: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    return result.stdout, result.stderr, result.returncode


def validate_json_schema(data, schema_path):
    """Validate JSON data against a schema file."""
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = json.load(f)

    try:
        jsonschema.validate(data, schema)
        return True
    except jsonschema.ValidationError as e:
        print(f"❌ Schema validation failed: {e.message}", file=sys.stderr)
        return False


def extract_tokens_from_json(output):
    """Extract tokens_used from JSON output."""
    try:
        data = json.loads(output)
        return data.get('tokens_used', 0)
    except:
        return 0


def extract_tokens_from_stderr(stderr):
    """Extract tokens_used from stderr log."""
    try:
        for line in stderr.split('\n'):
            if '"tokens_used"' in line:
                data = json.loads(line.strip())
                return data.get('tokens_used', 0)
    except:
        pass
    return 0


def run_test_case(test_case, project_root):
    """Run a single test case through the full pipeline."""
    print(f"\n=== Test: {test_case['name']} ===")
    print(f"Input: \"{test_case['input']}\"")

    tokens_total = 0

    # Step 1: Extract profile
    print("  Step 1: extract_profile...", end=' ')
    cmd = f'python scripts/extract_profile.py "{test_case["input"]}"'
    stdout, stderr, returncode = run_command(cmd)

    if returncode != 0:
        print(f"❌ Failed")
        return False

    result = json.loads(stdout)
    if result['status'] != 'success':
        print(f"❌ Error: {result['message']}")
        return False

    tokens_extract = result.get('tokens_used', 0)
    tokens_total += tokens_extract
    print(f"✓ {tokens_extract} tokens")

    # Validate criteria.json
    criteria_path = Path(result['file'])
    if not criteria_path.exists():
        print(f"❌ Criteria file not found: {criteria_path}")
        return False

    with open(criteria_path, 'r', encoding='utf-8') as f:
        criteria = json.load(f)

    # Validate schema
    schema_path = project_root / 'schemas' / 'user-profile.schema.json'
    if not validate_json_schema(criteria, schema_path):
        return False

    # Validate expectations
    if criteria.get('primary_genre') != test_case['expected_genre']:
        print(f"❌ Expected genre '{test_case['expected_genre']}' but got '{criteria.get('primary_genre')}'")
        return False

    if criteria.get('interaction_language') != test_case['expected_language']:
        print(f"❌ Expected language '{test_case['expected_language']}' but got '{criteria.get('interaction_language')}'")
        return False

    # Step 2: Vector search
    print("  Step 2: vector_search...", end=' ')
    results_path = project_root / '.cache' / 'search_results.json'
    cmd = f'python scripts/vector_search.py "{criteria_path}" > "{results_path}"'
    stdout, stderr, returncode = run_command(cmd)

    if returncode != 0:
        print(f"❌ Failed")
        return False

    print(f"✓ 0 tokens")

    # Validate results
    if not results_path.exists():
        print(f"❌ Results file not found: {results_path}")
        return False

    with open(results_path, 'r', encoding='utf-8') as f:
        results = json.load(f)

    if not results:
        print(f"❌ No results returned from vector search")
        return False

    # Step 3: Present recommendations
    print("  Step 3: present_recommendations...", end=' ')
    cmd = f'python scripts/present_recommendations.py --criteria "{criteria_path}" --results "{results_path}"'
    stdout, stderr, returncode = run_command(cmd)

    if returncode != 0:
        print(f"❌ Failed")
        return False

    tokens_present = extract_tokens_from_stderr(stderr)
    tokens_total += tokens_present
    print(f"✓ {tokens_present} tokens")

    # Validate markdown output
    markdown = stdout
    if not markdown:
        print(f"❌ No markdown output")
        return False

    # Check for expected language markers
    if test_case['expected_language'] == 'es':
        if 'Mejor Eleccion' not in markdown and 'Mejor Elección' not in markdown:
            print(f"❌ Spanish markdown markers not found in output")
            return False
    else:
        if 'Best Match' not in markdown:
            print(f"❌ English markdown markers not found in output")
            return False

    # Summary
    print(f"  Total: {tokens_total} tokens")

    return True


def main():
    """Main test runner."""
    print("=" * 60)
    print("Book Recommendation Pipeline Test Suite")
    print("=" * 60)

    # Check API key is set
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ ANTHROPIC_API_KEY environment variable not set")
        print("   Please set your API key:")
        print("   - Windows CMD: set ANTHROPIC_API_KEY=your_key_here")
        print("   - Windows PowerShell: $env:ANTHROPIC_API_KEY=\"your_key_here\"")
        print("   - Linux/Mac: export ANTHROPIC_API_KEY=your_key_here")
        sys.exit(1)
    print(f"✓ ANTHROPIC_API_KEY is set")

    # Determine project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Run test cases
    passed = 0
    failed = 0

    for test_case in TEST_CASES:
        try:
            if run_test_case(test_case, project_root):
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {str(e)}")
            failed += 1

    # Summary
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)
    else:
        print("\n✓ All tests passed!")
        sys.exit(0)


if __name__ == '__main__':
    main()
