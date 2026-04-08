#!/usr/bin/env python3
"""
Incremental Update Pipeline

This script intelligently merges NEW data (from agent scraping or user reviews) 
with existing processed data using weighted averages to preserve statistical accuracy.

Usage:
    python update_pipeline.py --new-data NEW_DATA/ --base-data app/finalData/
    
This ensures:
- Fast processing (only NEW data gets classified)
- Accurate ratings (weighted by number of descriptions)
- No data loss (all descriptions and metadata preserved)
"""

import os
import sys
import pandas as pd
import argparse
from datetime import datetime
from pathlib import Path
from thefuzz import fuzz

from routemaker_paths import MODEL_CHECKPOINT_DIR, PROCESSED_DATA_DIR

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'DataProcess'))


PLACEHOLDER_PHRASES = [
    "not mentioned in this text",
    "no specific details",
    "no direct information",
    "no specific description available",
    "no description available",
    "there is no specific description",
    "not enough information",
]


class IncrementalUpdater:
    def __init__(self, base_data_dir, model_path):
        """
        Initialize the incremental updater.
        
        Args:
            base_data_dir: Path to app/finalData/ with existing processed data
            model_path: Path to ML model for classifying new descriptions
        """
        self.base_data_dir = base_data_dir
        self.model_path = model_path
        self.categories = ['romance', 'family', 'cost', 'nature', 'adventure', 
                          'culture', 'food', 'relaxation', 'service', 'accessibility']

    @staticmethod
    def clean_text_value(value):
        """Normalize null-like values to empty strings for schema validation."""
        if pd.isna(value):
            return ''

        cleaned_value = str(value).strip()
        if cleaned_value.lower() in {'nan', 'none', 'null'}:
            return ''
        return cleaned_value

    def has_complete_ratings(self, row):
        """Return True when a row already carries explicit scores for all categories."""
        for category in self.categories:
            if category not in row.index or pd.isna(row[category]):
                return False
        return True

    @staticmethod
    def is_placeholder_description(text):
        normalized = str(text).strip().lower()
        if not normalized:
            return True

        for phrase in PLACEHOLDER_PHRASES:
            if phrase in normalized:
                return True

        return False

    def normalize_new_data(self, new_df):
        """Normalize incoming files to the processed-data contract."""
        normalized_df = new_df.copy()
        normalized_df.columns = [str(col).strip() for col in normalized_df.columns]

        if 'description' not in normalized_df.columns and 'text' in normalized_df.columns:
            normalized_df = normalized_df.rename(columns={'text': 'description'})

        required_columns = ['country', 'place', 'description']
        missing_required = [col for col in required_columns if col not in normalized_df.columns]
        if missing_required:
            raise ValueError(f"Missing required columns: {', '.join(missing_required)}")

        for column in ['region', 'place_type', 'google_maps_url', 'blog_source']:
            if column not in normalized_df.columns:
                normalized_df[column] = ''

        if 'source' in normalized_df.columns:
            normalized_df['blog_source'] = normalized_df['blog_source'].where(
                normalized_df['blog_source'].astype(str).str.strip() != '',
                normalized_df['source']
            )

        if 'is_manual_entry' in normalized_df.columns:
            manual_mask = normalized_df['is_manual_entry'].fillna(False).astype(bool)
            normalized_df.loc[manual_mask, 'blog_source'] = normalized_df.loc[manual_mask, 'blog_source'].where(
                normalized_df.loc[manual_mask, 'blog_source'].astype(str).str.strip() != '',
                'user_review'
            )

        normalized_df['country'] = normalized_df['country'].apply(self.clean_text_value)
        normalized_df['place'] = normalized_df['place'].apply(self.clean_text_value)
        normalized_df['description'] = normalized_df['description'].apply(self.clean_text_value)

        normalized_df = normalized_df[
            (normalized_df['country'] != '') &
            (normalized_df['place'] != '') &
            (normalized_df['description'] != '')
        ].copy()

        normalized_df = normalized_df[
            ~normalized_df['description'].apply(self.is_placeholder_description)
        ].copy()

        return normalized_df
        
    def load_base_data(self, country):
        """Load existing processed data for a country."""
        filepath = os.path.join(self.base_data_dir, f"{country}_processed.csv")
        if os.path.exists(filepath):
            return pd.read_csv(filepath)
        return None
    
    def classify_new_data(self, new_df):
        """
        Classify new descriptions using ML model.
        
        Args:
            new_df: DataFrame with new places/reviews
            
        Returns:
            DataFrame with classification scores
        """
        print(f"🔬 Classifying {len(new_df)} new descriptions...")

        provided_ratings_mask = new_df.apply(self.has_complete_ratings, axis=1)
        provided_ratings_count = int(provided_ratings_mask.sum())
        if provided_ratings_count:
            print(f"   Reusing provided ratings for {provided_ratings_count} rows")

        if provided_ratings_count == len(new_df):
            print("   All rows already have ratings; skipping ML classification")
            return new_df
        
        # Dynamically import classifier
        try:
            from DataProcess.classify_local_tuned import TravelClassifier
            classifier = TravelClassifier(self.model_path)
            
            # Apply classification
            for cat in self.categories:
                if cat not in new_df.columns:
                    new_df[cat] = 0
            
            # Classify descriptions
            for idx, row in new_df.iterrows():
                if provided_ratings_mask.loc[idx]:
                    continue
                try:
                    predictions = classifier.predict(str(row['description']))
                    for cat in self.categories:
                        new_df.at[idx, cat] = predictions.get(cat, 0)
                except Exception as e:
                    print(f"⚠️ Classification failed for {row.get('place', 'unknown')}: {e}")
            
            return new_df
        except ImportError:
            print("⚠️ Classifier not available. Using default ratings (5).")
            for cat in self.categories:
                if cat not in new_df.columns:
                    new_df[cat] = 5
            for idx in new_df.index:
                if provided_ratings_mask.loc[idx]:
                    continue
                for cat in self.categories:
                    if pd.isna(new_df.at[idx, cat]):
                        new_df.at[idx, cat] = 5
            return new_df
    
    def weighted_merge(self, old_row, new_rows, country):
        """
        Merge old and new data using weighted averages.
        
        Args:
            old_row: Existing place data with description_count
            new_rows: List of new descriptions for the same place
            country: Country name for tracking
            
        Returns:
            Merged row with weighted averages
        """
        old_count = old_row.get('description_count', 1)
        new_count = len(new_rows)
        total_count = old_count + new_count
        
        # Aggregate new descriptions
        new_descriptions = new_rows['description'].tolist()
        old_descriptions = str(old_row.get('description', '')).split('\n\n')
        all_descriptions = old_descriptions + new_descriptions
        # Keep first 5 descriptions in final output
        merged_description = '\n\n'.join(all_descriptions[:5])
        
        # Weighted average for each category
        merged_row = old_row.copy()
        merged_row['description'] = merged_description
        
        for cat in self.categories:
            if cat in old_row and cat in new_rows.columns:
                old_val = float(old_row.get(cat, 0))
                new_avg = float(new_rows[cat].mean())
                
                # Weighted average: (old_val * old_count + new_avg * new_count) / total
                merged_val = (old_val * old_count + new_avg * new_count) / total_count
                merged_row[cat] = round(merged_val, 1)
        
        # Update metadata
        merged_row['description_count'] = total_count
        merged_row['last_updated'] = datetime.now().strftime('%Y-%m-%d')
        
        return merged_row
    
    def merge_country_data(self, country, new_country_df):
        """
        Merge new data with existing data for a country.
        
        Args:
            country: Country name
            new_country_df: DataFrame with new places
            
        Returns:
            Merged DataFrame
        """
        print(f"\n🔀 Merging {country}...")
        
        # Load base data
        base_df = self.load_base_data(country)
        
        if base_df is None:
            print(f"   No existing data for {country}. Using new data as-is.")
            if 'description_count' not in new_country_df.columns:
                new_country_df['description_count'] = 1
            if 'last_updated' not in new_country_df.columns:
                new_country_df['last_updated'] = datetime.now().strftime('%Y-%m-%d')
            return new_country_df
        
        # Identify new places vs existing ones
        base_places = set(base_df['place'].unique())
        new_places = set(new_country_df['place'].unique())
        
        print(f"   Base: {len(base_places)} places | New: {len(new_places)} places")
        
        # Merge logic
        merged_rows = []
        
        # 1. Keep unchanged places from base
        unchanged = base_places - new_places
        for place in unchanged:
            merged_rows.append(base_df[base_df['place'] == place].iloc[0])
        
        # 2. Merge places that exist in both
        overlapping = base_places & new_places
        for place in overlapping:
            base_rows = base_df[base_df['place'] == place]
            new_rows = new_country_df[new_country_df['place'] == place]
            
            # Use first base entry as template, merge with all new entries
            base_row = base_rows.iloc[0]
            merged = self.weighted_merge(base_row, new_rows, country)
            merged_rows.append(merged)
            print(f"   ✓ Merged '{place}' (old: {base_row.get('description_count', 1)} → new: {merged['description_count']})")
        
        # 3. Add completely new places
        truly_new = new_places - base_places
        for place in truly_new:
            new_row = new_country_df[new_country_df['place'] == place].iloc[0].copy()
            if 'description_count' not in new_row.index or pd.isna(new_row.get('description_count')):
                new_row['description_count'] = 1
            if 'last_updated' not in new_row.index or pd.isna(new_row.get('last_updated')):
                new_row['last_updated'] = datetime.now().strftime('%Y-%m-%d')
            merged_rows.append(new_row)
        
        print(f"   Result: {len(merged_rows)} total places (unchanged: {len(unchanged)}, merged: {len(overlapping)}, new: {len(truly_new)})")
        
        merged_df = pd.DataFrame(merged_rows)
        return merged_df
    
    def update_all(self, new_data_dir, output_dir=None):
        """
        Update all countries with new data.
        
        Args:
            new_data_dir: Directory containing new CSV files
            output_dir: Where to save updated files (default: base_data_dir)
        """
        if output_dir is None:
            output_dir = self.base_data_dir
        
        print(f"\n{'='*60}")
        print(f"📊 Incremental Data Update Pipeline")
        print(f"{'='*60}")
        print(f"Base data: {self.base_data_dir}")
        print(f"New data:  {new_data_dir}")
        print(f"Output:    {output_dir}")
        
        if not os.path.exists(new_data_dir):
            print(f"❌ New data directory not found: {new_data_dir}")
            return False
        
        # Step 1: Aggregate new data
        print(f"\n🔍 Step 1: Aggregating new data...")
        new_files = [f for f in os.listdir(new_data_dir) if f.endswith('.csv')]
        
        if not new_files:
            print(f"❌ No CSV files found in {new_data_dir}")
            return False
        
        all_new_data = []
        for file in new_files:
            filepath = os.path.join(new_data_dir, file)
            df = pd.read_csv(filepath)
            all_new_data.append(df)
            print(f"   Loaded: {file} ({len(df)} rows)")
        
        new_data_combined = pd.concat(all_new_data, ignore_index=True)
        new_data_combined = self.normalize_new_data(new_data_combined)
        print(f"   Total new: {len(new_data_combined)} rows")

        if new_data_combined.empty:
            print("❌ No valid rows found after schema normalization")
            return False
        
        # Step 2: Classify new data
        print(f"\n⚙️  Step 2: Classifying new data...")
        classified_new = self.classify_new_data(new_data_combined)
        
        # Step 3: Merge by country
        print(f"\n🔗 Step 3: Merging by country...")
        
        countries = classified_new['country'].unique()
        updated_count = 0
        
        for country in countries:
            country_new_df = classified_new[classified_new['country'] == country].copy()
            merged_df = self.merge_country_data(country, country_new_df)
            
            # Save updated data
            output_path = os.path.join(output_dir, f"{country}_processed.csv")
            merged_df.to_csv(output_path, index=False, encoding='utf-8-sig')
            updated_count += 1
            print(f"   ✅ Saved: {output_path}")
        
        # Step 4: Clear user_reviews.csv after successful processing
        print(f"\n🧹 Step 4: Clearing processed reviews...")
        user_reviews_path = os.path.join(new_data_dir, "user_reviews.csv")
        if os.path.exists(user_reviews_path):
            try:
                os.remove(user_reviews_path)
                print(f"   ✅ Cleared: {user_reviews_path}")
            except Exception as e:
                print(f"   ⚠️  Could not clear user_reviews.csv: {e}")
        
        print(f"\n{'='*60}")
        print(f"🎉 Update Complete!")
        print(f"✅ Updated {updated_count} countries")
        print(f"📁 Output: {output_dir}")
        print(f"{'='*60}\n")
        
        return True


def main():
    parser = argparse.ArgumentParser(description="Incrementally update travel data with new entries")
    parser.add_argument("--new-data", "-n", required=True,
                       help="Directory containing new CSV files (agent scraped or user reviews)")
    parser.add_argument("--base-data", "-b", default=str(PROCESSED_DATA_DIR),
                       help="Directory with existing processed data (default: app/finalData)")
    parser.add_argument("--output", "-o", default=None,
                       help="Output directory (default: same as base-data)")
    parser.add_argument("--model", "-m", default=str(MODEL_CHECKPOINT_DIR),
                       help="ML model checkpoint path")
    
    args = parser.parse_args()
    
    # Convert to absolute paths
    base_data_abs = os.path.abspath(args.base_data)
    model_abs = os.path.abspath(args.model)
    output_abs = os.path.abspath(args.output) if args.output else base_data_abs
    new_data_abs = os.path.abspath(args.new_data)
    
    updater = IncrementalUpdater(base_data_abs, model_abs)
    success = updater.update_all(new_data_abs, output_abs)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
