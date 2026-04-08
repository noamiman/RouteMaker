#!/usr/bin/env python3
import argparse
from pathlib import Path

import pandas as pd

PLACEHOLDER_PHRASES = [
    "not mentioned in this text",
    "no specific details",
    "no direct information",
    "no specific description available",
    "no description available",
    "there is no specific description",
    "not enough information",
]

REQUIRED_COLUMNS = ["place", "country", "description"]


def count_placeholders(descriptions: pd.Series) -> int:
    lowered = descriptions.astype(str).str.lower()
    return int(lowered.apply(lambda t: any(p in t for p in PLACEHOLDER_PHRASES)).sum())


def validate_data_dir(data_dir: Path) -> int:
    files = sorted(data_dir.glob("*_processed.csv"))
    if not files:
        print(f"ERROR: No processed CSV files found in {data_dir}")
        return 1

    bad_files = []
    total_rows = 0
    total_placeholders = 0

    print("country_file,rows,missing_required,blank_descriptions,placeholder_descriptions")

    for file_path in files:
        df = pd.read_csv(file_path)
        total_rows += len(df)

        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        blank_descriptions = 0
        placeholders = 0

        if "description" in df.columns:
            descriptions = df["description"].astype(str)
            blank_descriptions = int((descriptions.str.strip() == "").sum())
            placeholders = count_placeholders(df["description"])
            total_placeholders += placeholders

        if missing:
            bad_files.append((file_path.name, f"missing columns: {', '.join(missing)}"))

        print(
            f"{file_path.name},{len(df)},{len(missing)},{blank_descriptions},{placeholders}"
        )

    print(
        f"SUMMARY files={len(files)} total_rows={total_rows} placeholder_rows={total_placeholders}"
    )

    if bad_files:
        print("ERRORS:")
        for file_name, message in bad_files:
            print(f"- {file_name}: {message}")
        return 2

    print("OK: Required schema present in all processed files")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate processed pipeline output")
    parser.add_argument(
        "--data-dir",
        default="app/finalData",
        help="Directory containing *_processed.csv files",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"ERROR: Data directory not found: {data_dir}")
        return 1

    return validate_data_dir(data_dir)


if __name__ == "__main__":
    raise SystemExit(main())
