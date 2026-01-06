import json
from pathlib import Path

def validate_newaukum_data():
    results_path = Path("./results/chunks/extracted_text.json")
    print(f"--- VALIDATING ORCHESTRATION INTEGRITY ---")
    
    if not results_path.exists():
        print("❌ FAIL: No extracted data found. Run 'RS 1: Ingest' task first.")
        return

    with open(results_path, 'r') as f:
        data = f.read().lower()

    # Factual Data Check (No Magic)
    benchmarks = {
        "Tree Replacement": "1.5 acre",
        "Cost Estimate": "$150/sf",
        "Clearance": "10'",
        "Bundle": "sr 92"
    }

    for key, val in benchmarks.items():
        if val.lower() in data:
            print(f"✅ PASSED: Found {key} ({val}) in local artifacts.")
        else:
            print(f"⚠️ WARNING: {key} missing from extraction. Check source PDF/PPTX.")

if __name__ == "__main__":
    validate_newaukum_data()