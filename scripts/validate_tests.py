#!/usr/bin/env python3
"""
Validate test structure and count tests

This script validates the test suite structure without running tests.
Useful for checking test organization before CI runs.
"""
import os
import ast
import sys
from pathlib import Path
from collections import defaultdict


def count_tests_in_file(filepath):
    """Count test functions in a Python file"""
    try:
        with open(filepath, 'r') as f:
            tree = ast.parse(f.read())

        test_count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name.startswith('test_'):
                    test_count += 1
        return test_count
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        return 0


def validate_test_structure():
    """Validate test directory structure"""
    test_dir = Path(__file__).parent.parent / 'tests'

    if not test_dir.exists():
        print("❌ Tests directory not found!")
        return False

    # Expected structure
    expected_dirs = ['unit', 'integration', 'fixtures']
    expected_files = ['conftest.py', '__init__.py']

    print("🔍 Validating test structure...")
    print(f"Test directory: {test_dir}\n")

    # Check directories
    for dir_name in expected_dirs:
        dir_path = test_dir / dir_name
        if dir_path.exists():
            print(f"✅ {dir_name}/ directory exists")
        else:
            print(f"⚠️  {dir_name}/ directory missing")

    # Check files
    for file_name in expected_files:
        file_path = test_dir / file_name
        if file_path.exists():
            print(f"✅ {file_name} exists")
        else:
            print(f"❌ {file_name} missing")

    return True


def count_all_tests():
    """Count all tests in the test suite"""
    test_dir = Path(__file__).parent.parent / 'tests'
    stats = defaultdict(int)

    print("\n📊 Test Statistics:\n")

    for test_type in ['unit', 'integration']:
        type_dir = test_dir / test_type
        if not type_dir.exists():
            continue

        print(f"\n{test_type.upper()} TESTS:")
        print("-" * 50)

        for test_file in sorted(type_dir.glob('test_*.py')):
            count = count_tests_in_file(test_file)
            stats[test_type] += count
            print(f"  {test_file.name:<40} {count:>3} tests")

    print("\n" + "=" * 50)
    print(f"Total unit tests:        {stats['unit']:>3}")
    print(f"Total integration tests: {stats['integration']:>3}")
    print(f"TOTAL TESTS:             {sum(stats.values()):>3}")
    print("=" * 50)

    return sum(stats.values())


def check_pytest_config():
    """Check pytest configuration"""
    pytest_ini = Path(__file__).parent.parent / 'pytest.ini'

    print("\n⚙️  Pytest Configuration:")
    print("-" * 50)

    if pytest_ini.exists():
        print("✅ pytest.ini found")
        with open(pytest_ini, 'r') as f:
            content = f.read()
            if 'testpaths' in content:
                print("✅ testpaths configured")
            if 'cov' in content:
                print("✅ coverage configured")
    else:
        print("⚠️  pytest.ini not found")


def check_ci_config():
    """Check CI/CD configuration"""
    ci_file = Path(__file__).parent.parent / '.github' / 'workflows' / 'ci.yml'

    print("\n🔄 CI/CD Configuration:")
    print("-" * 50)

    if ci_file.exists():
        print("✅ GitHub Actions workflow found")
        with open(ci_file, 'r') as f:
            content = f.read()
            if 'pytest' in content:
                print("✅ pytest configured in CI")
            if 'coverage' in content or 'cov' in content:
                print("✅ coverage reporting configured")
            if 'black' in content:
                print("✅ code formatting check configured")
            if 'ruff' in content or 'flake8' in content:
                print("✅ linting configured")
    else:
        print("⚠️  CI workflow not found")


def main():
    """Main validation function"""
    print("\n" + "=" * 50)
    print("  ENTERPRISE SEARCH - TEST VALIDATION")
    print("=" * 50 + "\n")

    validate_test_structure()
    total_tests = count_all_tests()
    check_pytest_config()
    check_ci_config()

    print("\n" + "=" * 50)
    if total_tests > 0:
        print(f"✅ Test suite validated successfully!")
        print(f"   Ready to run {total_tests} tests")
    else:
        print("⚠️  No tests found!")
        sys.exit(1)
    print("=" * 50 + "\n")

    print("Next steps:")
    print("  1. Run locally:  pytest tests/ -v")
    print("  2. With coverage: pytest --cov=src --cov-report=html")
    print("  3. CI will run automatically on push/PR")
    print()


if __name__ == "__main__":
    main()
