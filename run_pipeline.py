#!/usr/bin/env python3
"""
Travel Data Processing Pipeline Runner

This script runs the complete data processing pipeline:
1. Aggregate data by country (agg_by_country.py)
2. Classify places with ML model (classify_local_tuned.py)
3. Create final summarized results (final_result.py)

Usage:
    python run_pipeline.py [--force] [--skip-classification]

Arguments:
    --force: Force re-processing of all files
    --skip-classification: Skip the ML classification step
"""

import os
import sys
import argparse
import subprocess
import time
from pathlib import Path

from routemaker_paths import MODEL_CHECKPOINT_DIR, PROCESSED_DATA_DIR


def run_script(script_path, args=None, description=""):
    """Run a Python script and handle errors."""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")

    if not os.path.exists(script_path):
        print(f"❌ Error: Script not found: {script_path}")
        return False

    cmd = [sys.executable, script_path]
    if args:
        cmd.extend(args)

    try:
        start_time = time.time()
        result = subprocess.run(cmd, cwd=os.path.dirname(script_path))
        end_time = time.time()

        if result.returncode == 0:
            print(f"✅ Completed in {end_time - start_time:.2f} seconds")
            return True
        else:
            print(f"❌ Script failed with exit code: {result.returncode}")
            return False

    except Exception as e:
        print(f"❌ Error running script: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Run the travel data processing pipeline")
    parser.add_argument("--force", action="store_true",
                       help="Force re-processing of all files")
    parser.add_argument("--skip-classification", action="store_true",
                       help="Skip the ML classification step")
    args = parser.parse_args()

    # Define script paths relative to this file
    base_dir = Path(__file__).parent
    data_process_dir = base_dir / "DataProcess"

    scripts = {
        "agg_by_country.py": {
            "path": data_process_dir / "agg_by_country.py",
            "description": "Step 1: Aggregating data by country",
            "args": []
        },
        "classify_local_tuned.py": {
            "path": data_process_dir / "classify_local_tuned.py",
            "description": "Step 2: Classifying places with ML model",
            "args": ["--force"] if args.force else []
        },
        "final_result.py": {
            "path": data_process_dir / "final_result.py",
            "description": "Step 3: Creating final summarized results",
            "args": ["--overwrite"]
        }
    }

    print("🌍 Travel Data Processing Pipeline")
    print("=" * 60)

    # Check if required directories exist
    scraped_data_dir = base_dir / "ScrapedData"
    final_data_dir = PROCESSED_DATA_DIR
    model_dir = MODEL_CHECKPOINT_DIR

    if not scraped_data_dir.exists():
        print(f"❌ Error: ScrapedData directory not found: {scraped_data_dir}")
        return 1

    if not model_dir.exists() and not args.skip_classification:
        print(f"❌ Error: Model directory not found: {model_dir}")
        print("💡 Use --skip-classification to skip the ML step")
        return 1

    # Run pipeline steps
    success_count = 0
    total_steps = 3 if not args.skip_classification else 2

    # Step 1: Aggregate by country
    if run_script(str(scripts["agg_by_country.py"]["path"]),
                  scripts["agg_by_country.py"]["args"],
                  scripts["agg_by_country.py"]["description"]):
        success_count += 1
    else:
        print("❌ Pipeline failed at Step 1")
        return 1

    # Step 2: Classify (optional)
    if not args.skip_classification:
        if run_script(str(scripts["classify_local_tuned.py"]["path"]),
                      scripts["classify_local_tuned.py"]["args"],
                      scripts["classify_local_tuned.py"]["description"]):
            success_count += 1
        else:
            print("❌ Pipeline failed at Step 2")
            return 1

    # Step 3: Final results
    if run_script(str(scripts["final_result.py"]["path"]),
                  scripts["final_result.py"]["args"],
                  scripts["final_result.py"]["description"]):
        success_count += 1
    else:
        print("❌ Pipeline failed at Step 3")
        return 1

    # Summary
    print(f"\n{'='*60}")
    print("🎉 Pipeline completed successfully!")
    print(f"✅ Completed: {success_count}/{total_steps} steps")
    print(f"📁 Output location: {final_data_dir}")
    print(f"{'='*60}")

    return 0


if __name__ == "__main__":
    sys.exit(main())