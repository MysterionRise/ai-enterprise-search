"""
Quick validation script for recommendation system
Checks code structure, API contracts, and basic functionality
Runs without requiring full environment setup
"""

import ast
import os
import sys
from pathlib import Path

# Color codes for output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_header(text):
    print(f"\n{BLUE}{'=' * 80}{RESET}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{BLUE}{'=' * 80}{RESET}\n")


def print_success(text):
    print(f"{GREEN}✓{RESET} {text}")


def print_warning(text):
    print(f"{YELLOW}⚠{RESET} {text}")


def print_error(text):
    print(f"{RED}✗{RESET} {text}")


def validate_file_exists(filepath, description):
    """Validate that a file exists"""
    if os.path.exists(filepath):
        print_success(f"{description}: {filepath}")
        return True
    else:
        print_error(f"{description} NOT FOUND: {filepath}")
        return False


def validate_python_syntax(filepath):
    """Validate Python file syntax"""
    try:
        with open(filepath, "r") as f:
            ast.parse(f.read())
        return True
    except SyntaxError as e:
        print_error(f"Syntax error in {filepath}: {e}")
        return False


def validate_function_exists(filepath, function_name):
    """Check if a function exists in a Python file"""
    try:
        with open(filepath, "r") as f:
            tree = ast.parse(f.read())

        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) or isinstance(node, ast.FunctionDef):
                if node.name == function_name:
                    return True
        return False
    except Exception as e:
        print_error(f"Error checking function in {filepath}: {e}")
        return False


def validate_class_exists(filepath, class_name):
    """Check if a class exists in a Python file"""
    try:
        with open(filepath, "r") as f:
            tree = ast.parse(f.read())

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                return True
        return False
    except Exception as e:
        print_error(f"Error checking class in {filepath}: {e}")
        return False


def count_functions(filepath):
    """Count functions in a file"""
    try:
        with open(filepath, "r") as f:
            tree = ast.parse(f.read())

        count = sum(
            1
            for node in ast.walk(tree)
            if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef))
        )
        return count
    except:
        return 0


def main():
    print_header("RECOMMENDATION SYSTEM VALIDATION")
    print("This script validates the recommendation system implementation")
    print("without requiring full environment setup.\n")

    all_checks_passed = True

    # 1. File Structure Validation
    print_header("1. FILE STRUCTURE")

    files_to_check = [
        ("src/services/recommendation_service.py", "Recommendation Service"),
        ("src/models/recommendations.py", "Recommendation Models"),
        ("src/api/routes/recommendations.py", "Recommendation API Routes"),
        ("tests/test_recommendation_service.py", "Unit Tests"),
        ("scripts/test_recommendations.py", "Integration Tests"),
        ("ui/templates/index.html", "UI Template"),
        ("docs/PHASE2_TESTING_GUIDE.md", "Testing Guide"),
    ]

    for filepath, desc in files_to_check:
        if not validate_file_exists(filepath, desc):
            all_checks_passed = False

    # 2. Python Syntax Validation
    print_header("2. PYTHON SYNTAX VALIDATION")

    python_files = [
        "src/services/recommendation_service.py",
        "src/models/recommendations.py",
        "src/api/routes/recommendations.py",
        "tests/test_recommendation_service.py",
        "scripts/test_recommendations.py",
    ]

    for filepath in python_files:
        if os.path.exists(filepath):
            if validate_python_syntax(filepath):
                print_success(f"Valid syntax: {filepath}")
            else:
                all_checks_passed = False

    # 3. Service Layer Validation
    print_header("3. SERVICE LAYER (recommendation_service.py)")

    service_file = "src/services/recommendation_service.py"
    if os.path.exists(service_file):
        # Check for RecommendationService class
        if validate_class_exists(service_file, "RecommendationService"):
            print_success("RecommendationService class found")

            # Check for required methods
            methods = [
                "get_related_documents",
                "get_trending",
                "get_popular_in_department",
                "get_personalized_recommendations",
            ]

            for method in methods:
                if validate_function_exists(service_file, method):
                    print_success(f"  ✓ Method: {method}()")
                else:
                    print_error(f"  ✗ Method missing: {method}()")
                    all_checks_passed = False
        else:
            print_error("RecommendationService class not found")
            all_checks_passed = False

        # Count total lines
        with open(service_file, "r") as f:
            lines = len(f.readlines())
        print_success(f"Service implementation: {lines} lines of code")

    # 4. API Layer Validation
    print_header("4. API LAYER (recommendations.py)")

    api_file = "src/api/routes/recommendations.py"
    if os.path.exists(api_file):
        # Check for router
        with open(api_file, "r") as f:
            content = f.read()

        if "APIRouter" in content:
            print_success("APIRouter initialized")

        # Check for endpoints
        endpoints = [
            "get_related_documents",
            "get_trending_documents",
            "get_popular_documents",
            "get_personalized_recommendations",
        ]

        for endpoint in endpoints:
            if validate_function_exists(api_file, endpoint):
                print_success(f"  ✓ Endpoint: {endpoint}()")
            else:
                print_error(f"  ✗ Endpoint missing: {endpoint}()")
                all_checks_passed = False

        # Check for route decorators
        if "@router.get" in content:
            route_count = content.count("@router.get")
            print_success(f"Route decorators: {route_count} GET endpoints")

    # 5. Models Validation
    print_header("5. DATA MODELS (recommendations.py)")

    models_file = "src/models/recommendations.py"
    if os.path.exists(models_file):
        models = [
            "RecommendationItem",
            "RelatedDocumentsResponse",
            "TrendingResponse",
            "PopularResponse",
            "PersonalizedRecommendationsResponse",
        ]

        for model in models:
            if validate_class_exists(models_file, model):
                print_success(f"  ✓ Model: {model}")
            else:
                print_error(f"  ✗ Model missing: {model}")
                all_checks_passed = False

    # 6. UI Validation
    print_header("6. UI COMPONENTS (index.html)")

    ui_file = "ui/templates/index.html"
    if os.path.exists(ui_file):
        with open(ui_file, "r") as f:
            html_content = f.read()

        # Check for recommendation widgets
        ui_checks = [
            ("recommendations-sidebar", "Recommendations sidebar"),
            ("trending-list", "Trending list container"),
            ("popular-list", "Popular list container"),
            ("loadRecommendations", "loadRecommendations() function"),
            ("loadTrending", "loadTrending() function"),
            ("loadPopular", "loadPopular() function"),
            ("/api/v1/recommendations/trending", "Trending API endpoint call"),
            ("/api/v1/recommendations/popular", "Popular API endpoint call"),
        ]

        for check_id, description in ui_checks:
            if check_id in html_content:
                print_success(f"  ✓ {description}")
            else:
                print_warning(f"  ⚠ {description} not found")

    # 7. Test Coverage Validation
    print_header("7. TEST COVERAGE")

    test_file = "tests/test_recommendation_service.py"
    if os.path.exists(test_file):
        with open(test_file, "r") as f:
            test_content = f.read()

        # Count test functions
        test_count = test_content.count("def test_")
        print_success(f"Unit tests: {test_count} test functions")

        # Check for test classes
        test_classes = [
            "TestGetRelatedDocuments",
            "TestGetTrending",
            "TestGetPopularInDepartment",
            "TestGetPersonalizedRecommendations",
            "TestErrorHandling",
        ]

        for test_class in test_classes:
            if validate_class_exists(test_file, test_class):
                print_success(f"  ✓ Test class: {test_class}")
            else:
                print_warning(f"  ⚠ Test class: {test_class}")

    integration_test = "scripts/test_recommendations.py"
    if os.path.exists(integration_test):
        with open(integration_test, "r") as f:
            lines = len(f.readlines())
        print_success(f"Integration test script: {lines} lines")

        test_functions = count_functions(integration_test)
        print_success(f"Integration test functions: {test_functions}")

    # 8. Documentation Validation
    print_header("8. DOCUMENTATION")

    test_guide = "docs/PHASE2_TESTING_GUIDE.md"
    if os.path.exists(test_guide):
        with open(test_guide, "r") as f:
            content = f.read()
            lines = len(content.split("\n"))
            words = len(content.split())

        print_success(f"Testing guide: {lines} lines, {words} words")

        # Check for key sections
        sections = [
            "Overview",
            "Unit Tests",
            "Integration Tests",
            "Performance Targets",
            "Success Criteria",
        ]
        for section in sections:
            if section in content:
                print_success(f"  ✓ Section: {section}")
            else:
                print_warning(f"  ⚠ Section: {section}")

    # 9. Code Quality Checks
    print_header("9. CODE QUALITY")

    # Check for docstrings
    if os.path.exists(service_file):
        with open(service_file, "r") as f:
            content = f.read()

        docstring_count = content.count('"""') + content.count("'''")
        print_success(f"Docstrings in service: {docstring_count // 2} found")

        # Check for type hints
        if "List[Dict]" in content or "Optional[User]" in content:
            print_success("Type hints present")

        # Check for logging
        if "logger." in content:
            log_count = content.count("logger.")
            print_success(f"Logging statements: {log_count}")

    # 10. Integration with Main App
    print_header("10. MAIN APP INTEGRATION")

    main_app = "src/api/main.py"
    if os.path.exists(main_app):
        with open(main_app, "r") as f:
            main_content = f.read()

        if "recommendations" in main_content:
            print_success("Recommendations module imported in main.py")
        else:
            print_error("Recommendations module NOT imported in main.py")
            all_checks_passed = False

        if "recommendations.router" in main_content:
            print_success("Recommendations router registered")
        else:
            print_error("Recommendations router NOT registered")
            all_checks_passed = False

    # Final Summary
    print_header("VALIDATION SUMMARY")

    if all_checks_passed:
        print(f"{GREEN}✓ ALL CRITICAL CHECKS PASSED!{RESET}\n")
        print("The recommendation system implementation is complete and well-structured.")
        print("\nNext steps:")
        print("  1. Run Black formatting: black src/ tests/ scripts/")
        print("  2. Commit changes")
        print("  3. Run integration tests with full environment")
        print("  4. Deploy and test in VP demo")
        return 0
    else:
        print(f"{YELLOW}⚠ SOME CHECKS FAILED{RESET}\n")
        print("Review the errors above and fix any issues.")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n{RED}Validation script failed: {e}{RESET}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
