#!/usr/bin/env python3
"""
CTO HYGIENE INTEGRITY AUDIT
Validates that the application hygiene sweep was successful.
"""

import os
from pathlib import Path


def check_hygiene():
    """Execute comprehensive hygiene audit."""
    print("\n" + "="*60)
    print("CTO HYGIENE INTEGRITY AUDIT")
    print("="*60 + "\n")
    
    passed = 0
    failed = 0
    warnings = 0
    
    # 1. Check .gitignore exists
    print("1️⃣  GITIGNORE VALIDATION")
    if Path(".gitignore").exists():
        print("   ✅ PASSED: .gitignore is present")
        passed += 1
        
        # Check contents
        gitignore_content = Path(".gitignore").read_text()
        required_patterns = [".venv/", "sources/", "results/", "*.json"]
        missing = [p for p in required_patterns if p not in gitignore_content]
        if not missing:
            print("   ✅ PASSED: All required exclusion patterns present")
            passed += 1
        else:
            print(f"   ❌ FAIL: Missing patterns: {missing}")
            failed += 1
    else:
        print("   ❌ FAIL: .gitignore missing from root")
        failed += 1
    
    # 2. Check for data leaks in root
    print("\n2️⃣  DATA LEAK DETECTION")
    root_files = list(Path(".").glob("*"))
    root_files = [f.name for f in root_files if f.is_file()]
    
    # Files that are OK in root
    allowed_in_root = {
        'README.md', 'AGENTS.md', 'USER_MANUAL.md',
        'pyproject.toml', '.gitignore', '.gitattributes',
        'setup.py', 'LICENSE', '.python-version'
    }
    
    # Dangerous patterns
    dangerous_extensions = {'.json', '.md', '.xlsx'}
    leaks = []
    
    for f in root_files:
        ext = Path(f).suffix.lower()
        if ext in dangerous_extensions and f not in allowed_in_root:
            leaks.append(f)
    
    if not leaks:
        print("   ✅ PASSED: No data leaks detected in root")
        passed += 1
    else:
        print(f"   ⚠️  WARNING: Leaked files in root ({len(leaks)}): {', '.join(leaks[:5])}")
        warnings += 1
    
    # 3. Check directory structure
    print("\n3️⃣  DIRECTORY STRUCTURE VALIDATION")
    required_dirs = {
        'src': "Source code package",
        'tests': "Test suite",
        'results': "Output artifacts",
        'sources': "Input documents",
    }
    
    missing_dirs = []
    for dir_name, desc in required_dirs.items():
        if Path(dir_name).exists():
            print(f"   ✅ {dir_name:15} - {desc}")
            passed += 1
        else:
            print(f"   ❌ {dir_name:15} - MISSING")
            missing_dirs.append(dir_name)
            failed += 1
    
    # 4. Check entry point configuration
    print("\n4️⃣  ENTRY POINT VALIDATION")
    pyproject = Path("pyproject.toml")
    if pyproject.exists():
        content = pyproject.read_text()
        if 'research-synth = "research_synth.cli:app"' in content:
            print("   ✅ PASSED: Entry point correctly configured")
            print("      Command: research-synth = research_synth.cli:app")
            passed += 1
        else:
            print("   ❌ FAIL: Entry point not found in pyproject.toml")
            failed += 1
    
    # 5. Check for legacy artifacts
    print("\n5️⃣  LEGACY ARTIFACT CHECK")
    legacy_dir = Path("legacy")
    if legacy_dir.exists() and legacy_dir.is_dir():
        legacy_files = list(legacy_dir.glob("*"))
        print(f"   ✅ PASSED: legacy/ directory exists ({len(legacy_files)} files)")
        passed += 1
    else:
        print("   ⚠️  NOTE: legacy/ directory not found (optional)")
        warnings += 1
    
    # 6. Check .venv is ignored
    print("\n6️⃣  VENV ISOLATION CHECK")
    venv_path = Path(".venv")
    gitignore_text = Path(".gitignore").read_text()
    
    if venv_path.exists():
        print("   ℹ️  .venv directory exists locally")
        if ".venv/" in gitignore_text:
            print("   ✅ PASSED: .venv/ is in .gitignore")
            passed += 1
        else:
            print("   ❌ FAIL: .venv/ not in .gitignore - RISK OF COMMIT")
            failed += 1
    else:
        print("   ℹ️  .venv not present (virtual environment not created yet)")
    
    # Summary
    print("\n" + "="*60)
    print("AUDIT SUMMARY")
    print("="*60)
    print(f"✅ Passed:  {passed}")
    print(f"⚠️  Warning: {warnings}")
    print(f"❌ Failed:  {failed}")
    
    if failed == 0:
        print("\n🎉 HYGIENE STATUS: CLEAN & PROFESSIONAL")
        print("   Application is ready for distribution.")
        return True
    else:
        print("\n⚠️  HYGIENE STATUS: ISSUES DETECTED")
        print("   Please resolve failing checks before deployment.")
        return False


if __name__ == "__main__":
    success = check_hygiene()
    exit(0 if success else 1)
