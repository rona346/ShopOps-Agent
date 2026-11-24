"""
Automated Test Runner for ShopOps Agent Backend.
Runs all test modules across Phases 2, 3, 4, 5, and 6 using Python's unittest framework.
"""

import sys
import unittest
from pathlib import Path

# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Import all test suites across phases
import tests.test_auth_api as test_auth_api
import tests.test_agent_api as test_agent_api
import tests.test_agent_service as test_agent_service
import tests.test_analysis_api as test_analysis_api
import tests.test_analysis_service as test_analysis_service
import tests.test_approval_api as test_approval_api
import tests.test_approval_service as test_approval_service
import tests.test_execution_api as test_execution_api
import tests.test_execution_service as test_execution_service
import tests.test_firestore_unconfigured as test_firestore_unconfigured
import tests.test_inventory_api as test_inventory_api
import tests.test_models as test_models
import tests.test_supabase_repositories as test_supabase_repositories


def run_all_tests():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Phase 2: Inventory models, API, and Firestore unconfigured handling (22 tests)
    suite.addTests(loader.loadTestsFromModule(test_models))
    suite.addTests(loader.loadTestsFromModule(test_inventory_api))
    suite.addTests(loader.loadTestsFromModule(test_firestore_unconfigured))

    # Phase 3: Inventory analysis and reorder planning (12 tests)
    suite.addTests(loader.loadTestsFromModule(test_analysis_service))
    suite.addTests(loader.loadTestsFromModule(test_analysis_api))

    # Phase 4: Gemini AI Agent engine and natural language Q&A (10 tests)
    suite.addTests(loader.loadTestsFromModule(test_agent_service))
    suite.addTests(loader.loadTestsFromModule(test_agent_api))

    # Phase 5: Owner approval workflow (22 tests)
    suite.addTests(loader.loadTestsFromModule(test_approval_service))
    suite.addTests(loader.loadTestsFromModule(test_approval_api))

    # Phase 6: Action execution and reorder tasks (14 tests)
    suite.addTests(loader.loadTestsFromModule(test_execution_service))
    suite.addTests(loader.loadTestsFromModule(test_execution_api))

    # Phase 9: Authentication & API Security (26 tests)
    suite.addTests(loader.loadTestsFromModule(test_auth_api))

    # Modules 2 & 3: Supabase PostgreSQL Repositories (7 tests)
    suite.addTests(loader.loadTestsFromModule(test_supabase_repositories))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    print("TEST EXECUTION SUMMARY:")
    print(f"Total Tests Run: {result.testsRun}")
    print(f"Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 60)

    if not result.wasSuccessful():
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()
