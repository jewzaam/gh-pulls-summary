#!/usr/bin/env python3
"""
Convenience script to run integration tests with proper setup and validation.
"""

import os
import sys
import subprocess
import time
import requests

def check_github_connectivity():
    """Check if GitHub API is accessible."""
    try:
        response = requests.get("https://api.github.com/rate_limit", timeout=5)
        if response.status_code == 200:
            data = response.json()
            remaining = data.get("rate", {}).get("remaining", 0)
            print(f"✓ GitHub API accessible. Rate limit remaining: {remaining}")
            return True
        else:
            print(f"✗ GitHub API returned status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Cannot connect to GitHub API: {e}")
        return False

def check_test_repo():
    """Check if the test repository is accessible."""
    try:
        response = requests.get("https://api.github.com/repos/jewzaam/gh-pulls-summary", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Test repository accessible: {data.get('full_name')}")
            return True
        else:
            print(f"✗ Test repository returned status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Cannot access test repository: {e}")
        return False

def main():
    print("GitHub Pull Request Summary Tool - Integration Tests")
    print("=" * 55)
    
    # Check GitHub token status
    github_token = os.environ.get("GITHUB_TOKEN")
    if github_token:
        print(f"✓ GitHub token detected (length: {len(github_token)})")
        print("  Higher rate limits will be available")
    else:
        print("⚠ No GitHub token detected")
        print("  Using unauthenticated requests (60/hour limit)")
    
    print()
    
    # Check connectivity
    print("Checking prerequisites...")
    if not check_github_connectivity():
        print("Cannot proceed without GitHub API access")
        sys.exit(1)
    
    if not check_test_repo():
        print("Cannot proceed without test repository access")
        sys.exit(1)
    
    print()
    
    # Set environment variable
    os.environ["RUN_INTEGRATION_TESTS"] = "1"
    
    # Run the tests
    print("Running integration tests...")
    print("-" * 30)
    
    try:
        # Run with verbose output (simplified tests first)
        result = subprocess.run([
            sys.executable, "-m", "unittest", 
            "discover", "-s", "integration_tests", "-p", "test_integration_simple.py", "-v"
        ], check=False, capture_output=False)
        
        print("-" * 30)
        
        if result.returncode == 0:
            print("✓ All integration tests passed!")
        else:
            print(f"✗ Integration tests failed with exit code: {result.returncode}")
            sys.exit(result.returncode)
    
    except KeyboardInterrupt:
        print("\n⚠ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error running tests: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 