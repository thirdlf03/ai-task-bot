#!/usr/bin/env python
"""Test script for intelligent code reading"""

from pathlib import Path
from src.repository.analyzer import RepositoryAnalyzer
from src.repository.code_parser import CodeParser

def test_code_parser():
    """Test CodeParser with a real file"""
    print("\n=== Testing CodeParser ===")

    parser = CodeParser()
    test_file = Path("src/ai/workflow.py")

    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return

    definitions = parser.extract_functions_and_classes(test_file)
    print(f"✓ Found {len(definitions)} functions/classes in {test_file}")

    for i, definition in enumerate(definitions[:3], 1):
        print(f"\n{i}. {definition['type']}: {definition['name']}")
        if definition['docstring']:
            print(f"   Docstring: {definition['docstring'][:50]}...")
        print(f"   Lines: {definition['start_line']}-{definition['end_line']}")

def test_ripgrep_search():
    """Test ripgrep search"""
    print("\n=== Testing Ripgrep Search ===")

    analyzer = RepositoryAnalyzer(Path("."))
    keywords = ["workflow", "task"]

    files = analyzer.ripgrep_search(keywords)
    print(f"✓ Found {len(files)} files matching keywords {keywords}")

    for i, file_path in enumerate(files[:5], 1):
        print(f"  {i}. {file_path}")

def test_intelligent_reading():
    """Test intelligent code reading"""
    print("\n=== Testing Intelligent Code Reading ===")

    analyzer = RepositoryAnalyzer(Path("."))
    keywords = ["workflow", "breakdown"]

    code_content = analyzer.read_code_intelligently(keywords, max_functions=5, max_chars=5000)

    print(f"✓ Extracted intelligent code content")
    print(f"  Length: {len(code_content)} characters")

    # Show first few lines
    lines = code_content.split('\n')[:15]
    print("\n  Preview:")
    for line in lines:
        print(f"  {line}")

    if len(lines) > 15:
        print("  ...")

if __name__ == "__main__":
    print("Starting intelligent code reading tests...\n")

    try:
        test_code_parser()
        test_ripgrep_search()
        test_intelligent_reading()

        print("\n" + "="*50)
        print("✅ All tests completed successfully!")
        print("="*50)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
