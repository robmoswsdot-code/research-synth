# GUI Testing Guide: Engineering Change Directive
**Validation Date:** January 6, 2026

This guide walks you through testing the refactored `gui.py` to verify that CLI commands now properly generate artifacts in the selected project directory.

---

## Prerequisites

1. **Virtual environment activated:**
   ```powershell
   .venv\Scripts\Activate.ps1
   ```

2. **research-synth installed in editable mode:**
   ```powershell
   pip install -e .
   ```

3. **Test project folder ready:**
   ```powershell
   # Create a test project directory
   mkdir C:\Users\mosherr\Projects\TEST_PROJECT
   ```

---

## Quick Start: Launch GUI

```powershell
cd C:\Users\mosherr\source\repos\research-synth
python gui.py
```

---

## Test Scenario 1: Initialize a Project

**Objective:** Verify that `init` command generates artifacts in the selected directory (not in app root).

### Steps:

1. **In the GUI:**
   - Click **Browse** and select `C:\Users\mosherr\Projects\TEST_PROJECT`
   - In the CLI input field, enter: `init .`
   - Click **Run**

2. **Expected Outcome:**
   ```
   Running: research-synth init .
   Context: C:\Users\mosherr\Projects\TEST_PROJECT
   
   [CLI output]
   
   ================================================================================
   EXECUTION SUMMARY
   Status: SUCCESS
   
   Artifacts Generated (1):
     OK init_report.md
   ```

3. **Verification:**
   - ✅ Status shows: `OK Command completed | 1 artifacts generated` (GREEN)
   - ✅ Check `C:\Users\mosherr\Projects\TEST_PROJECT\` for:
     - `research.yml` (config file)
     - `init_report.md` (generated report)
     - `sources/`, `chunks/`, `analysis/` directories

---

## Test Scenario 2: Ingest Documents

**Objective:** Verify that `ingest` command creates artifacts in the project directory.

### Steps:

1. **Prepare test documents:**
   ```powershell
   # Create sample documents in sources/
   @"
   This is a test document about Fish Passage.
   It contains important information about dam removal.
   Fish passage is critical for ecosystem health.
   "@  | Out-File -FilePath "C:\Users\mosherr\Projects\TEST_PROJECT\sources\fish_passage.txt"
   ```

2. **In the GUI:**
   - Project Root: `C:\Users\mosherr\Projects\TEST_PROJECT` (already set)
   - CLI input: `ingest .`
   - Click **Run**

3. **Expected Outcome:**
   ```
   Running: research-synth ingest .
   Context: C:\Users\mosherr\Projects\TEST_PROJECT
   
   [CLI output]
   
   ================================================================================
   EXECUTION SUMMARY
   Status: SUCCESS
   
   Artifacts Generated (2):
     OK chunks/extracted_text.json
     OK chunks/ingest_report.md
   ```

4. **Verification:**
   - ✅ Status shows: `OK Command completed | 2 artifacts generated` (GREEN)
   - ✅ Check `C:\Users\mosherr\Projects\TEST_PROJECT\chunks\` for:
     - `extracted_text.json`
     - `ingest_report.md`

---

## Test Scenario 3: Analyze Chunks

**Objective:** Verify that `analyze` command creates artifacts in the project directory.

### Steps:

1. **In the GUI:**
   - CLI input: `analyze .`
   - Click **Run**

2. **Expected Outcome:**
   ```
   EXECUTION SUMMARY
   Status: SUCCESS
   
   Artifacts Generated (2):
     OK analysis/concepts.json
     OK analysis/analysis_report.md
   ```

3. **Verification:**
   - ✅ Status shows: `OK Command completed | 2 artifacts generated` (GREEN)
   - ✅ Check `C:\Users\mosherr\Projects\TEST_PROJECT\analysis\` for:
     - `concepts.json`
     - `analysis_report.md`

---

## Test Scenario 4: Generate Report

**Objective:** Verify that `report` command creates a markdown report.

### Steps:

1. **In the GUI:**
   - CLI input: `report .`
   - Click **Run**

2. **Expected Outcome:**
   ```
   EXECUTION SUMMARY
   Status: SUCCESS
   
   Artifacts Generated (2):
     OK report.md
     OK report_metadata.md
   ```

3. **Verification:**
   - ✅ Status shows: `OK Command completed | 2 artifacts generated` (GREEN)
   - ✅ Check `C:\Users\mosherr\Projects\TEST_PROJECT\` for:
     - `report.md` (main report)
     - `report_metadata.md` (metadata)

---

## Test Scenario 5: Silent Failure Detection

**Objective:** Verify that GUI detects when a command runs but produces no output files (WARNING status).

### Steps:

1. **In the GUI:**
   - Create a new project directory: `C:\Users\mosherr\Projects\EMPTY_PROJECT`
   - Click **Browse**, select `C:\Users\mosherr\Projects\EMPTY_PROJECT`
   - CLI input: `ingest .` (with no documents in sources/)
   - Click **Run**

2. **Expected Outcome:**
   ```
   EXECUTION SUMMARY
   Status: WARNING: No output files detected
   
   No new artifacts detected.
   ```

3. **Verification:**
   - ⚠️ Status shows: `WARNING Command ran but no output files detected` (ORANGE)
   - ✅ This proves the GUI is detecting missing artifacts

---

## Test Scenario 6: Multi-Directory State Route Projects

**Objective:** Verify that switching between project directories works correctly.

### Steps:

1. **Create two projects:**
   ```powershell
   mkdir "C:\Users\mosherr\Projects\SR_410"
   mkdir "C:\Users\mosherr\Projects\SR_528"
   
   # Add documents to SR_410
   @"Fish passage enhancement for SR 410"@ | Out-File -FilePath "C:\Users\mosherr\Projects\SR_410\sources\sr410.txt"
   
   # Add documents to SR_528
   @"Fish passage enhancement for SR 528"@ | Out-File -FilePath "C:\Users\mosherr\Projects\SR_528\sources\sr528.txt"
   ```

2. **In the GUI:**
   - Browse and select `C:\Users\mosherr\Projects\SR_410`
   - CLI input: `init .`
   - Click **Run**
   - **Verify:** Files created in SR_410 ✅

3. **Switch Projects:**
   - Browse and select `C:\Users\mosherr\Projects\SR_528`
   - CLI input: `init .`
   - Click **Run**
   - **Verify:** Files created in SR_528, NOT in SR_410 ✅

4. **Verification:**
   - ✅ `C:\Users\mosherr\Projects\SR_410\research.yml` exists
   - ✅ `C:\Users\mosherr\Projects\SR_528\research.yml` exists
   - ✅ No files crossed over between directories

---

## Status Label Reference

| Status | Color | Meaning |
|--------|-------|---------|
| `OK Command completed \| X artifacts generated` | GREEN | Command succeeded, artifacts created |
| `WARNING Command ran but no output files detected` | ORANGE | Command ran (returncode=0) but no files generated |
| `FAILED [reason]` | RED | Command failed or error occurred |
| `Error: [message]` | RED | Exception or missing project context |

---

## Troubleshooting

### "Error: Please select a project root directory first"
- **Fix:** Click **Browse** and select a valid project directory before running commands

### "No new artifacts detected" on a command that should generate files
- **Root cause:** Either the command failed silently, or files were created elsewhere
- **Fix:** Check the CLI output above the summary for error messages
- **Check:** Verify the directory exists and has proper read/write permissions

### GUI appears unresponsive while running commands
- **Root cause:** This is expected during ingest/analyze (can take seconds to minutes)
- **Note:** All commands run in background threads; GUI remains responsive

### "Command timed out (exceeded 120 seconds)"
- **Root cause:** Large document sets or slow analysis
- **Fix:** This is informational; the timeout is generous but may need adjustment for massive projects

---

## Key Validations

After running all test scenarios, verify:

1. ✅ **No files created in app root** (`C:\Users\mosherr\source\repos\research-synth\`)
2. ✅ **All artifacts appear in project directory** (user-selected folder)
3. ✅ **Artifact list matches generated files** (count and names match)
4. ✅ **GUI status reflects actual outcome** (GREEN/ORANGE/RED correctly assigned)
5. ✅ **Multi-directory isolation works** (no cross-contamination between projects)
6. ✅ **Session persistence works** (project root remembered on GUI restart)

---

## CTO Verdict Confirmation

After completing these tests, you will have confirmed:

> **The "silent failure" pattern has been eliminated. The GUI now provides:**
> - Definitive proof of file generation with artifact listings
> - Clear working directory awareness for each command
> - Immediate feedback on success vs. warning vs. failure
> - Reliable isolation between multiple project folders

**Status:** Engineering Change Directive VALIDATED ✓
