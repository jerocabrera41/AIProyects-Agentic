#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Structural validation script - validates files and schemas without API calls.
"""

import json
import sys
import os
from pathlib import Path

# Force UTF-8 output encoding on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def validate_file_exists(path, name):
    """Check if a file exists."""
    if Path(path).exists():
        print(f"✓ {name} exists")
        return True
    else:
        print(f"❌ {name} missing: {path}")
        return False


def validate_json_file(path, name):
    """Check if a JSON file is valid."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            json.load(f)
        print(f"✓ {name} is valid JSON")
        return True
    except Exception as e:
        print(f"❌ {name} invalid: {str(e)}")
        return False


def validate_python_syntax(path, name):
    """Check if a Python file has valid syntax."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            compile(f.read(), path, 'exec')
        print(f"✓ {name} has valid Python syntax")
        return True
    except SyntaxError as e:
        print(f"❌ {name} syntax error: {str(e)}")
        return False


def main():
    print("=" * 60)
    print("Structure Validation (No API Required)")
    print("=" * 60)

    project_root = Path(__file__).parent.parent
    checks_passed = 0
    checks_total = 0

    # Python scripts
    print("\n[Python Scripts]")
    scripts = [
        ('scripts/extract_profile.py', 'extract_profile.py'),
        ('scripts/present_recommendations.py', 'present_recommendations.py'),
        ('scripts/vector_search.py', 'vector_search.py'),
        ('scripts/test_pipeline.py', 'test_pipeline.py'),
    ]

    for path, name in scripts:
        full_path = project_root / path
        checks_total += 2
        if validate_file_exists(full_path, name):
            checks_passed += 1
        if validate_python_syntax(full_path, name):
            checks_passed += 1

    # JSON schemas
    print("\n[JSON Schemas]")
    schemas = [
        ('schemas/user-profile.schema.json', 'user-profile.schema.json'),
        ('schemas/recommendation.schema.json', 'recommendation.schema.json'),
    ]

    for path, name in schemas:
        full_path = project_root / path
        checks_total += 2
        if validate_file_exists(full_path, name):
            checks_passed += 1
        if validate_json_file(full_path, name):
            checks_passed += 1

    # Data files
    print("\n[Data Files]")
    data_files = [
        ('data/genre-mapping.json', 'genre-mapping.json'),
        ('data/genre-adjacency.json', 'genre-adjacency.json'),
        ('data/catalog_with_embeddings.json', 'catalog_with_embeddings.json'),
    ]

    for path, name in data_files:
        full_path = project_root / path
        checks_total += 2
        if validate_file_exists(full_path, name):
            checks_passed += 1
        if validate_json_file(full_path, name):
            checks_passed += 1

    # Reference files
    print("\n[Reference Files]")
    ref_files = [
        ('.claude/agents/profile-extractor.md', 'profile-extractor.md'),
        ('.claude/agents/recommendation-presenter.md', 'recommendation-presenter.md'),
        ('prompts/recommendation-format.md', 'recommendation-format.md'),
    ]

    for path, name in ref_files:
        full_path = project_root / path
        checks_total += 1
        if validate_file_exists(full_path, name):
            checks_passed += 1

    # Infrastructure
    print("\n[Infrastructure]")
    infra_files = [
        ('requirements.txt', 'requirements.txt'),
        ('.gitignore', '.gitignore'),
        ('CLAUDE.md', 'CLAUDE.md'),
        ('docs/tools-documentation.md', 'tools-documentation.md'),
    ]

    for path, name in infra_files:
        full_path = project_root / path
        checks_total += 1
        if validate_file_exists(full_path, name):
            checks_passed += 1

    # Summary
    print("\n" + "=" * 60)
    print(f"Validation Results: {checks_passed}/{checks_total} checks passed")
    print("=" * 60)

    if checks_passed == checks_total:
        print("\n✓ All structural validations passed!")
        print("\nNext steps:")
        print("1. Install dependencies: python -m pip install anthropic")
        print("2. Set ANTHROPIC_API_KEY environment variable")
        print("3. Run: python scripts/test_pipeline.py")
        sys.exit(0)
    else:
        print(f"\n❌ {checks_total - checks_passed} checks failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
