"""
Comprehensive test runner for Project Caesar
Runs unit tests, integration tests, error handling tests, and performance tests
"""

import sys
import os
import time
from typing import Dict, List

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def run_basic_tests() -> bool:
    """Run the basic unit tests"""
    print("🧪 Running Basic Unit Tests")
    print("=" * 50)
    
    try:
        from run_tests import run_tests
        return run_tests()
    except Exception as e:
        print(f"❌ Error running basic tests: {e}")
        return False

def run_integration_tests() -> bool:
    """Run integration tests"""
    print("\n🔗 Running Integration Tests")
    print("=" * 50)
    
    try:
        sys.path.insert(0, os.path.join(project_root, 'tests', 'integration_tests'))
        from test_complete_system import run_integration_tests
        return run_integration_tests()
    except Exception as e:
        print(f"❌ Error running integration tests: {e}")
        return False

def run_error_handling_tests() -> bool:
    """Run error handling tests"""
    print("\n🔍 Running Error Handling Tests")
    print("=" * 50)
    
    try:
        sys.path.insert(0, os.path.join(project_root, 'tests', 'agent_tests'))
        from test_error_handling import run_error_handling_tests
        return run_error_handling_tests()
    except Exception as e:
        print(f"❌ Error running error handling tests: {e}")
        return False

def run_performance_tests() -> bool:
    """Run performance tests"""
    print("\n⚡ Running Performance Tests")
    print("=" * 50)
    
    try:
        sys.path.insert(0, os.path.join(project_root, 'tests', 'agent_tests'))
        from test_performance import run_performance_tests
        return run_performance_tests()
    except Exception as e:
        print(f"❌ Error running performance tests: {e}")
        return False

def run_static_analysis() -> Dict[str, List[str]]:
    """Run basic static analysis checks"""
    print("\n📋 Running Static Analysis")
    print("=" * 50)
    
    issues = {
        'imports': [],
        'syntax': [],
        'style': []
    }
    
    # Check agent modules
    agent_dir = os.path.join(project_root, 'agent')
    if os.path.exists(agent_dir):
        for filename in os.listdir(agent_dir):
            if filename.endswith('.py'):
                filepath = os.path.join(agent_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        content = f.read()
                    
                    # Check for basic issues
                    if 'except:' in content:
                        issues['style'].append(f"{filename}: Contains bare except clause")
                    
                    if 'import *' in content:
                        issues['style'].append(f"{filename}: Contains wildcard import")
                    
                    # Try to compile the file
                    compile(content, filepath, 'exec')
                    
                except SyntaxError as e:
                    issues['syntax'].append(f"{filename}: Syntax error - {e}")
                except Exception as e:
                    issues['imports'].append(f"{filename}: Import/compilation error - {e}")
    
    # Report issues
    total_issues = sum(len(issue_list) for issue_list in issues.values())
    if total_issues == 0:
        print("✅ No static analysis issues found!")
    else:
        print(f"⚠️  Found {total_issues} potential issues:")
        for category, issue_list in issues.items():
            if issue_list:
                print(f"\n{category.upper()}:")
                for issue in issue_list:
                    print(f"  - {issue}")
    
    return issues

def generate_test_report(results: Dict[str, bool], issues: Dict[str, List[str]]) -> None:
    """Generate a comprehensive test report"""
    print("\n" + "=" * 70)
    print("📊 COMPREHENSIVE TEST REPORT")
    print("=" * 70)
    
    # Test results summary
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    
    print(f"\n🧪 Test Suite Results:")
    print(f"   Total Test Suites: {total_tests}")
    print(f"   Passed: {passed_tests}")
    print(f"   Failed: {total_tests - passed_tests}")
    print(f"   Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    # Individual test results
    print(f"\n📋 Individual Results:")
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {test_name:25} {status}")
    
    # Static analysis summary
    print(f"\n🔍 Static Analysis:")
    total_issues = sum(len(issue_list) for issue_list in issues.values())
    if total_issues == 0:
        print("   ✅ No issues found")
    else:
        print(f"   ⚠️  {total_issues} issues found")
        for category, count in {k: len(v) for k, v in issues.items()}.items():
            if count > 0:
                print(f"     {category}: {count}")
    
    # Overall status
    all_passed = all(results.values())
    has_critical_issues = any(issues['syntax']) or any(issues['imports'])
    
    print(f"\n🎯 Overall Status:")
    if all_passed and not has_critical_issues:
        print("   🎉 ALL SYSTEMS GO! Project Caesar is ready for deployment.")
    elif all_passed and has_critical_issues:
        print("   ⚠️  Tests passed but critical issues found. Review before deployment.")
    else:
        print("   ❌ Some tests failed. Fix issues before deployment.")
    
    # Recommendations
    print(f"\n💡 Recommendations:")
    if not all_passed:
        failed_tests = [name for name, result in results.items() if not result]
        print(f"   • Fix failing tests: {', '.join(failed_tests)}")
    
    if issues['style']:
        print("   • Address style issues for better code quality")
    
    if issues['syntax'] or issues['imports']:
        print("   • Critical: Fix syntax and import errors immediately")
    
    if all_passed and total_issues == 0:
        print("   • Consider adding more edge case tests")
        print("   • Monitor performance in production")
        print("   • Set up continuous integration")

def main():
    """Main test runner"""
    start_time = time.time()
    
    print("🚀 Project Caesar - Comprehensive Test Suite")
    print("=" * 70)
    print("Testing AI-powered in-car assistant simulation system")
    print("=" * 70)
    
    # Run all test suites
    results = {}
    
    # Basic unit tests
    results['Unit Tests'] = run_basic_tests()
    
    # Integration tests
    results['Integration Tests'] = run_integration_tests()
    
    # Error handling tests
    results['Error Handling'] = run_error_handling_tests()
    
    # Performance tests
    results['Performance Tests'] = run_performance_tests()
    
    # Static analysis
    issues = run_static_analysis()
    
    # Generate comprehensive report
    end_time = time.time()
    total_time = end_time - start_time
    
    generate_test_report(results, issues)
    
    print(f"\n⏱️  Total test execution time: {total_time:.2f} seconds")
    print("=" * 70)
    
    # Return overall success
    all_passed = all(results.values())
    critical_issues = any(issues['syntax']) or any(issues['imports'])
    
    return all_passed and not critical_issues

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
