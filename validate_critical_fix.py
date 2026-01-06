#!/usr/bin/env python3
"""
CRITICAL FIX VALIDATION TEST
Ensures the one-line fix resolves the silent failure issue.
"""
import tempfile
from pathlib import Path
import sys
sys.path.insert(0, '.')
from gui import run_cli_command

print("=" * 80)
print("CRITICAL FIX VALIDATION TEST")
print("Emergency Directive: CLI Artifact Generation Failure Resolution")
print("=" * 80)

with tempfile.TemporaryDirectory() as tmpdir:
    tmpdir = Path(tmpdir)
    
    test_results = []
    
    # Test 1: INIT command
    print("\n[TEST 1] INIT Command")
    output, artifacts, status = run_cli_command(['init', '.'], str(tmpdir))
    success = status == "SUCCESS" and len(artifacts) > 0
    test_results.append(("INIT", success))
    print(f"Status: {status} | Artifacts: {len(artifacts)}")
    if artifacts:
        for a in artifacts:
            print(f"  ✓ {a}")
    
    # Test 2: Create test document
    print("\n[SETUP] Create Test Document")
    sources = tmpdir / 'sources'
    sources.mkdir(exist_ok=True)
    (sources / 'test_document.txt').write_text(
        """
        Fish Passage Enhancement Project
        
        This project focuses on ecological restoration by implementing
        fish passage improvements in the Newaukum Creek watershed.
        Key objectives include dam removal, habitat restoration, and
        species recovery monitoring.
        """
    )
    print(f"Created: sources/test_document.txt")
    
    # Test 3: INGEST command
    print("\n[TEST 2] INGEST Command")
    output, artifacts, status = run_cli_command(['ingest', '.'], str(tmpdir))
    success = status == "SUCCESS" and len(artifacts) >= 2
    test_results.append(("INGEST", success))
    print(f"Status: {status} | Artifacts: {len(artifacts)}")
    if artifacts:
        for a in artifacts:
            print(f"  ✓ {a}")
    
    # Test 4: ANALYZE command
    print("\n[TEST 3] ANALYZE Command")
    output, artifacts, status = run_cli_command(['analyze', '.'], str(tmpdir))
    success = status == "SUCCESS" and len(artifacts) >= 2
    test_results.append(("ANALYZE", success))
    print(f"Status: {status} | Artifacts: {len(artifacts)}")
    if artifacts:
        for a in artifacts:
            print(f"  ✓ {a}")
    
    # Test 5: REPORT command
    print("\n[TEST 4] REPORT Command")
    output, artifacts, status = run_cli_command(['report', '.'], str(tmpdir))
    success = status == "SUCCESS" and len(artifacts) >= 2
    test_results.append(("REPORT", success))
    print(f"Status: {status} | Artifacts: {len(artifacts)}")
    if artifacts:
        for a in artifacts:
            print(f"  ✓ {a}")
    
    # Summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    
    all_files = list(tmpdir.rglob('*'))
    file_count = len([f for f in all_files if f.is_file()])
    
    print(f"\nTest Results:")
    for test_name, passed in test_results:
        status_str = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status_str}: {test_name}")
    
    print(f"\nFile Generation:")
    print(f"  Total Files Created: {file_count}")
    
    all_passed = all(result[1] for result in test_results)
    
    print("\n" + "=" * 80)
    if all_passed and file_count > 0:
        print("✓✓✓ CRITICAL FIX VALIDATED ✓✓✓")
        print("\nThe one-line CLI invocation fix RESOLVES the silent failure issue.")
        print("All commands now generate artifacts correctly in project directories.")
        print("\nStatus: ✅ READY FOR PRODUCTION DEPLOYMENT")
    else:
        print("✗✗✗ VALIDATION FAILED ✗✗✗")
        print("Fix did not resolve the issue. Further investigation needed.")
        print("\nStatus: ❌ REQUIRES TROUBLESHOOTING")
    print("=" * 80)
    
    sys.exit(0 if all_passed else 1)
